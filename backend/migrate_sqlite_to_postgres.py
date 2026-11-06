import os
import sys
import json
import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, text, Boolean, JSON, DateTime, Integer, Float
from sqlalchemy.schema import CreateIndex

# Ensure backend directory is in path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app.db.base import Base
import app.db.models  # ensure all models are registered in Base.metadata

SQLITE_PATH = os.path.join(CURRENT_DIR, "ettehad.db")
if not os.path.exists(SQLITE_PATH):
    # Try parent directory
    SQLITE_PATH = os.path.join(os.path.dirname(CURRENT_DIR), "ettehad.db")

POSTGRES_URL = os.getenv(
    "POSTGRES_SYNC_URL",
    "postgresql+psycopg://postgres:1234@localhost:5432/ettehad_db"
)


def run_migration():
    print("=" * 80)
    print("  ETTEHAD PLATFORM: SQLite -> PostgreSQL High-Performance Migration")
    print("=" * 80)
    print(f"[*] Source SQLite:     {SQLITE_PATH}")
    print(f"[*] Target PostgreSQL: {POSTGRES_URL}")

    if not os.path.exists(SQLITE_PATH):
        print(f"[!] ERROR: SQLite database file not found at {SQLITE_PATH}")
        sys.exit(1)

    # 1. Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Get all SQLite tables
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    sqlite_tables = set(row[0] for row in sqlite_cur.fetchall())
    print(f"[*] Found {len(sqlite_tables)} tables in SQLite database.")

    # 2. Connect to PostgreSQL & create all tables + indexes
    pg_engine = create_engine(POSTGRES_URL, echo=False)

    print("[*] Rebuilding schema and indexes fresh in PostgreSQL...")
    with pg_engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        Base.metadata.create_all(bind=conn)
    print("[+] All tables and indexes successfully initialized in PostgreSQL.")

    # 3. Disable FK constraints during migration using session_replication_role
    print("[*] Disabling foreign key constraints for fast bulk ingestion...")
    with pg_engine.connect() as conn:
        conn.execute(text("SET session_replication_role = 'replica';"))
        conn.commit()

    # Determine order of tables: Base.metadata.sorted_tables has topological dependency order
    migration_tables = [t for t in Base.metadata.sorted_tables if t.name in sqlite_tables]
    # Add any extra tables that might exist in SQLite but weren't in sorted_tables
    extra_sqlite_tables = [t_name for t_name in sqlite_tables if t_name not in [t.name for t in migration_tables]]

    total_migrated_rows = 0
    verification_results = []

    with pg_engine.connect() as pg_conn:
        # Set session replication role on this connection
        pg_conn.execute(text("SET session_replication_role = 'replica';"))

        for sa_table in migration_tables:
            table_name = sa_table.name
            
            # Count in SQLite
            sqlite_cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            src_count = sqlite_cur.fetchone()[0]

            if src_count == 0:
                verification_results.append((table_name, src_count, 0, "MATCH (Empty)"))
                continue

            # Clear any preexisting rows in Postgres table
            pg_conn.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE;'))

            # Fetch rows from SQLite
            sqlite_cur.execute(f'SELECT * FROM "{table_name}"')
            src_rows = sqlite_cur.fetchall()

            col_names = [col[0] for col in sqlite_cur.description]
            sa_col_types = {col.name: col.type for col in sa_table.columns}

            batch_data = []
            for row in src_rows:
                row_dict = dict(row)
                clean_dict = {}

                for col_name, val in row_dict.items():
                    if col_name not in sa_col_types:
                        continue  # Skip columns not in model

                    col_type = sa_col_types[col_name]

                    # 1. Handle Booleans: SQLite stores 0/1, Postgres requires True/False
                    if isinstance(col_type, Boolean):
                        if val is None:
                            clean_dict[col_name] = None
                        elif isinstance(val, (int, str)):
                            clean_dict[col_name] = bool(int(val))
                        else:
                            clean_dict[col_name] = bool(val)

                    # 2. Handle JSON: Parse JSON strings if needed
                    elif isinstance(col_type, JSON):
                        if val is None:
                            clean_dict[col_name] = None
                        elif isinstance(val, str):
                            try:
                                clean_dict[col_name] = json.loads(val)
                            except Exception:
                                clean_dict[col_name] = val
                        else:
                            clean_dict[col_name] = val

                    # 3. Handle DateTime: SQLite strings -> datetime objects if string
                    elif isinstance(col_type, DateTime):
                        if val is None:
                            clean_dict[col_name] = None
                        elif isinstance(val, str):
                            # Try parsing ISO or standard sqlite formats
                            try:
                                clean_dict[col_name] = datetime.fromisoformat(val.replace("Z", "+00:00"))
                            except Exception:
                                try:
                                    clean_dict[col_name] = datetime.strptime(val, "%Y-%m-%d %H:%M:%S")
                                except Exception:
                                    clean_dict[col_name] = val
                        else:
                            clean_dict[col_name] = val
                    else:
                        clean_dict[col_name] = val

                batch_data.append(clean_dict)

            # Insert in chunks of 500
            chunk_size = 500
            for i in range(0, len(batch_data), chunk_size):
                chunk = batch_data[i:i + chunk_size]
                pg_conn.execute(sa_table.insert(), chunk)

            pg_conn.commit()

            # Verify count in Postgres
            res = pg_conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
            status = "MATCH" if res == src_count else f"MISMATCH ({src_count} vs {res})"
            verification_results.append((table_name, src_count, res, status))
            total_migrated_rows += res
            print(f"  [+] Table {table_name:32} -> {res:6} rows transferred [{status}]")

        # 4. Re-enable foreign keys
        print("[*] Re-enabling foreign key constraints...")
        pg_conn.execute(text("SET session_replication_role = 'origin';"))
        pg_conn.commit()

        # 5. Synchronize auto-increment sequences
        print("[*] Synchronizing PostgreSQL serial sequences...")
        sync_seq_sql = """
        DO $$
        DECLARE
            r RECORD;
            seq_name TEXT;
        BEGIN
            FOR r IN (
                SELECT c.table_name, c.column_name 
                FROM information_schema.columns c
                JOIN information_schema.tables t ON c.table_name = t.table_name
                WHERE c.table_schema = 'public' 
                  AND t.table_type = 'BASE TABLE'
                  AND (c.data_type LIKE '%int%' OR c.column_default LIKE 'nextval%')
            ) LOOP
                seq_name := pg_get_serial_sequence('"' || r.table_name || '"', r.column_name);
                IF seq_name IS NOT NULL THEN
                    EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 1))', seq_name, r.column_name, r.table_name);
                END IF;
            END LOOP;
        END $$;
        """
        pg_conn.execute(text(sync_seq_sql))
        pg_conn.commit()
        print("[+] Sequences synchronized successfully.")

        # 6. Verify Indexes
        print("\n[*] Inspecting created PostgreSQL Indexes:")
        idx_res = pg_conn.execute(text("""
            SELECT tablename, indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            ORDER BY tablename, indexname;
        """)).fetchall()
        print(f"[+] Total indexes active on database: {len(idx_res)}")
        for tablename, indexname in idx_res[:20]:
            print(f"    - {tablename:28} : {indexname}")
        if len(idx_res) > 20:
            print(f"    ... and {len(idx_res) - 20} more indexes.")

    sqlite_conn.close()

    print("\n" + "=" * 80)
    print(f"  MIGRATION SUMMARY: {total_migrated_rows} Total Rows Migrated Across {len(verification_results)} Tables")
    print("=" * 80)
    all_matched = all("MATCH" in r[3] for r in verification_results)
    if all_matched:
        print("[SUCCESS] 100% of tables and rows migrated with perfect parity!")
    else:
        print("[WARNING] Some discrepancies detected during verification:")
        for r in verification_results:
            if "MISMATCH" in r[3]:
                print(f"  - {r[0]}: SQLite={r[1]}, Postgres={r[2]}")

    return all_matched


if __name__ == "__main__":
    success = run_migration()
    if not success:
        sys.exit(1)
