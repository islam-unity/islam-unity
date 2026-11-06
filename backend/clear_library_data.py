import os
import sys
import shutil
import sqlite3
from pathlib import Path

# Setup paths
root_dir = Path(__file__).resolve().parent.parent
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.services.vector_service import VectorService
from app.config import settings

def clean_database(db_path: Path):
    if not db_path.exists():
        print(f"⚠️ پایگاه داده در مسیر {db_path} یافت نشد.")
        return

    print(f"🧹 پاکسازی پایگاه داده: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get count of knowledge_chunks
    try:
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
        chunks_count = cur.fetchone()[0]
        cur.execute("DELETE FROM knowledge_chunks")
        print(f"   • حذف {chunks_count} چانک از جدول knowledge_chunks")
    except sqlite3.OperationalError as e:
        print(f"   • جدول knowledge_chunks وجود ندارد: {e}")

    # Delete non-seed books
    try:
        cur.execute("SELECT id, title FROM books WHERE id NOT IN ('book_nahj', 'book_forty_hadith', 'bk_fake_wahdat_01')")
        books_to_delete = cur.fetchall()
        for b_id, b_title in books_to_delete:
            cur.execute("DELETE FROM book_chapters WHERE book_id = ?", (b_id,))
            cur.execute("DELETE FROM reading_progress WHERE book_id = ?", (b_id,))
            cur.execute("DELETE FROM book_highlights WHERE book_id = ?", (b_id,))
            cur.execute("DELETE FROM book_favorites WHERE book_id = ?", (b_id,))
            cur.execute("DELETE FROM shelf_books WHERE book_id = ?", (b_id,))
            cur.execute("DELETE FROM books WHERE id = ?", (b_id,))
            print(f"   • حذف کتاب '{b_title}' ({b_id}) و فصول مربوطه")
    except sqlite3.OperationalError as e:
        print(f"   • خطا در جدول books/chapters: {e}")

    conn.commit()
    conn.close()
    print(f"✅ پایگاه داده {db_path.name} با موفقیت پاکسازی شد.")

def clean_qdrant():
    print("🧹 پاکسازی بردارهای کیودرانت (Qdrant)...")
    try:
        client = VectorService.get_client()
        collections = [c.name for c in client.get_collections().collections]
        col_name = settings.QDRANT_COLLECTION
        if col_name in collections:
            client.delete_collection(col_name)
            print(f"   • کالکشن '{col_name}' حذف شد.")
        VectorService._ensure_collection(client, col_name)
        print(f"   • کالکشن تازه و خالی '{col_name}' ایجاد شد.")
        print("✅ کیودرانت با موفقیت ریست شد.")
    except Exception as e:
        print(f"⚠️ خطا در پاکسازی کیودرانت: {e}")

def clean_media_exports():
    print("🧹 پاکسازی فایل‌های کش خروجی هوش مصنوعی (ai_exports)...")
    dirs = [
        backend_dir / "media" / "ai_exports",
        root_dir / "media" / "ai_exports"
    ]
    for d in dirs:
        if d.exists():
            for item in d.glob("*.*"):
                try:
                    item.unlink()
                    print(f"   • حذف فایل کش: {item.name}")
                except Exception as ex:
                    print(f"   • خطا در حذف {item.name}: {ex}")
    print("✅ فایل‌های خروجی موقت پاکسازی شدند.")

def main():
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("==================================================")
    print("🚀 شروع فرآیند پاکسازی داده‌های کتابخانه و چانک‌ها")
    print("==================================================")
    clean_database(backend_dir / "ettehad.db")
    clean_database(root_dir / "ettehad.db")
    clean_qdrant()
    clean_media_exports()
    print("==================================================")
    print("🎉 تمام داده‌ها با موفقیت پاکسازی شدند و سیستم آماده ورود داده جدید است.")
    print("==================================================")

if __name__ == "__main__":
    main()
