"""
Standalone Empirical Verification Runner for Milestone M1 Fast Actions
Produces verbatim logs of API requests, responses, envelopes, and direct SQLite database queries.
"""

import asyncio
import os
import sys
import sqlite3
import json
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.seed_data import seed_database
from app.db.models import (
    User, ConsultationThread, ConsultationMessage,
    Post, PostReport, DeveloperAccount, DeveloperApiKey
)

TEST_DB_FILE = "./test_m1_standalone.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def query_sqlite(query: str, params: tuple = ()) -> list:
    conn = sqlite3.connect(TEST_DB_FILE)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        conn.close()


async def run_verification():
    print("=" * 80)
    print("EMPIRICAL VERIFICATION HARNESS - MILESTONE M1 FAST ACTIONS & DB STATE MUTATIONS")
    print("=" * 80)

    # 1. Database Setup
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)

    print(f"\n[INIT] Initializing isolated SQLite test database: {TEST_DB_FILE}")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        await seed_database(session)

        # Seed test PostReport
        rep = PostReport(
            id="rep_m1_emp_01",
            post_id="post_fiqh_crypto_01",
            user_id="usr_seeker_1",
            reason="INAPPROPRIATE_BEHAVIOR",
            description="گزارش تجربی جهت صحت‌سنجی عملیات سریع ادمین",
            status="PENDING",
            created_at=datetime.now(timezone.utc)
        )
        session.add(rep)

        # Seed test DeveloperAccount and DeveloperApiKey
        dev_acc = DeveloperAccount(
            id="dev_acc_m1_01",
            user_id="usr_seeker_1",
            app_name="سیستم معارفی تست ادمین",
            tier="ENTERPRISE",
            monthly_quota_tokens=5000000,
            used_tokens_this_month=0,
            rate_limit_per_minute=120,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(dev_acc)

        dev_key = DeveloperApiKey(
            id="key_m1_emp_01",
            account_id="dev_acc_m1_01",
            key_hash="hash_m1_verification_key",
            key_prefix="ak_live_m1",
            label="کلید معتبر تست M1",
            is_active=True,
            total_requests=0,
            total_tokens=0,
            created_at=datetime.now(timezone.utc)
        )
        session.add(dev_key)

        await session.commit()
    print("[INIT] Database initialized and seeded successfully.")

    app.dependency_overrides[get_db] = override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

        # ---------------------------------------------------------------------
        # ACTION 1: PATCH /api/v1/admin/users/{id}/status
        # ---------------------------------------------------------------------
        print("\n" + "-" * 70)
        print("ACTION 1: PATCH /api/v1/admin/users/{id}/status")
        print("-" * 70)
        u_id = "usr_seeker_1"
        row = query_sqlite("SELECT is_active FROM users WHERE id = ?", (u_id,))
        print(f"  [1.0 DB PRE-STATE] SQLite row: is_active = {row[0][0]}")

        # Toggle to False
        patch_res1 = await client.patch(f"/api/v1/admin/users/{u_id}/status", json={"is_active": False})
        print(f"  [1.1 MUTATION -> False] HTTP {patch_res1.status_code}")
        body1 = patch_res1.json()
        print(f"      Envelope: success={body1.get('success')}, timestamp={body1.get('timestamp')}")
        print(f"      Returned data: isActive={body1['data'].get('isActive')}, is_active={body1['data'].get('is_active')}")
        assert patch_res1.status_code == 200
        assert body1["success"] is True
        assert body1["data"]["isActive"] is False

        # Verify DB directly
        row = query_sqlite("SELECT is_active FROM users WHERE id = ?", (u_id,))
        print(f"  [1.2 DB POST-STATE -> False] SQLite row: is_active = {row[0][0]}")
        assert row[0][0] in (0, False)

        # Verify GET API
        get_res1 = await client.get(f"/api/v1/admin/users/{u_id}")
        assert get_res1.status_code == 200
        assert get_res1.json()["data"]["isActive"] is False
        print(f"  [1.3 GET API] Verified user is_active=False via GET endpoint.")

        # Toggle back to True
        patch_res2 = await client.patch(f"/api/v1/admin/users/{u_id}/status", json={"is_active": True})
        print(f"  [1.4 MUTATION -> True] HTTP {patch_res2.status_code}")
        body2 = patch_res2.json()
        print(f"      Returned data: isActive={body2['data'].get('isActive')}, is_active={body2['data'].get('is_active')}")
        assert patch_res2.status_code == 200
        assert body2["data"]["isActive"] is True

        # Verify DB directly
        row = query_sqlite("SELECT is_active FROM users WHERE id = ?", (u_id,))
        print(f"  [1.5 DB POST-STATE -> True] SQLite row: is_active = {row[0][0]}")
        assert row[0][0] in (1, True)
        print("  -> ACTION 1 EMPIRICALLY CONFIRMED (PASS)")

        # ---------------------------------------------------------------------
        # ACTION 2: PATCH /api/v1/admin/consultations/threads/{id}/status
        # ---------------------------------------------------------------------
        print("\n" + "-" * 70)
        print("ACTION 2: PATCH /api/v1/admin/consultations/threads/{id}/status")
        print("-" * 70)
        t_id = "thread_839210"
        row = query_sqlite("SELECT status FROM consultation_threads WHERE id = ?", (t_id,))
        print(f"  [2.0 DB PRE-STATE] SQLite row: status = {row[0][0]}")

        # Update status to ANSWERED
        patch_t = await client.patch(f"/api/v1/admin/consultations/threads/{t_id}/status", json={"status": "ANSWERED"})
        print(f"  [2.1 MUTATION -> ANSWERED] HTTP {patch_t.status_code}")
        t_body = patch_t.json()
        print(f"      Envelope: success={t_body.get('success')}, timestamp={t_body.get('timestamp')}")
        print(f"      Returned data: status={t_body['data'].get('status')}")
        assert patch_t.status_code == 200
        assert t_body["success"] is True
        assert t_body["data"]["status"] == "ANSWERED"

        # Verify DB directly
        row = query_sqlite("SELECT status FROM consultation_threads WHERE id = ?", (t_id,))
        print(f"  [2.2 DB POST-STATE] SQLite row: status = {row[0][0]}")
        assert row[0][0] == "ANSWERED"

        # Verify GET API
        get_t = await client.get(f"/api/v1/admin/consultations/threads/{t_id}")
        assert get_t.status_code == 200
        assert get_t.json()["data"]["status"] == "ANSWERED"
        print(f"  [2.3 GET API] Verified thread status=ANSWERED via GET endpoint.")
        print("  -> ACTION 2 EMPIRICALLY CONFIRMED (PASS)")

        # ---------------------------------------------------------------------
        # ACTION 3: POST /api/v1/admin/consultations/threads/{id}/reply
        # ---------------------------------------------------------------------
        print("\n" + "-" * 70)
        print("ACTION 3: POST /api/v1/admin/consultations/threads/{id}/reply")
        print("-" * 70)
        msgs_cnt_pre = query_sqlite("SELECT COUNT(*) FROM consultation_messages WHERE thread_id = ?", (t_id,))[0][0]
        print(f"  [3.0 DB PRE-STATE] SQLite count of messages in thread: {msgs_cnt_pre}")

        reply_payload = {
            "text": "سلام علیکم. پاسخ تخصصی مشاور فقهی ثبت گردید.",
            "sender_role": "SCHOLAR",
            "citation": "کتاب مکاسب، شیخ انصاری، باب خیارات"
        }
        reply_res = await client.post(f"/api/v1/admin/consultations/threads/{t_id}/reply", json=reply_payload)
        print(f"  [3.1 POST QUICK REPLY] HTTP {reply_res.status_code}")
        r_body = reply_res.json()
        print(f"      Envelope: success={r_body.get('success')}, timestamp={r_body.get('timestamp')}")
        msg_id = r_body["data"]["id"]
        print(f"      Created message id: {msg_id}, senderRole={r_body['data'].get('senderRole')}")
        assert reply_res.status_code == 200
        assert r_body["success"] is True
        assert r_body["data"]["threadId"] == t_id
        assert r_body["data"]["text"] == reply_payload["text"]

        # Verify DB directly
        msg_db = query_sqlite("SELECT id, thread_id, text, citation FROM consultation_messages WHERE id = ?", (msg_id,))
        print(f"  [3.2 DB POST-STATE] SQLite row for message {msg_id}:")
        print(f"      thread_id = {msg_db[0][1]}")
        print(f"      text = {msg_db[0][2]}")
        print(f"      citation = {msg_db[0][3]}")
        assert len(msg_db) == 1
        assert msg_db[0][1] == t_id
        assert msg_db[0][2] == reply_payload["text"]

        # Verify thread detail API contains the new message
        get_t_msgs = await client.get(f"/api/v1/admin/consultations/threads/{t_id}")
        assert get_t_msgs.status_code == 200
        thread_messages = get_t_msgs.json()["data"]["messages"]
        assert any(m["id"] == msg_id for m in thread_messages)
        print(f"  [3.3 GET API] Verified new message exists in thread detail message list.")
        print("  -> ACTION 3 EMPIRICALLY CONFIRMED (PASS)")

        # ---------------------------------------------------------------------
        # ACTION 4: PATCH /api/v1/admin/feed/reports/{id}/status
        # ---------------------------------------------------------------------
        print("\n" + "-" * 70)
        print("ACTION 4: PATCH /api/v1/admin/feed/reports/{id}/status")
        print("-" * 70)
        rep_id = "rep_m1_emp_01"
        target_post_id = "post_fiqh_crypto_01"
        rep_row_pre = query_sqlite("SELECT status FROM post_reports WHERE id = ?", (rep_id,))
        post_row_pre = query_sqlite("SELECT status FROM posts WHERE id = ?", (target_post_id,))
        print(f"  [4.0 DB PRE-STATE] Report status = {rep_row_pre[0][0]}, Post status = {post_row_pre[0][0]}")

        # Update report status to RESOLVED_REMOVED
        patch_rep = await client.patch(
            f"/api/v1/admin/feed/reports/{rep_id}/status",
            json={"status": "RESOLVED_REMOVED"}
        )
        print(f"  [4.1 MUTATION -> RESOLVED_REMOVED] HTTP {patch_rep.status_code}")
        rep_body = patch_rep.json()
        print(f"      Envelope: success={rep_body.get('success')}, timestamp={rep_body.get('timestamp')}")
        print(f"      Returned report data: status={rep_body['data'].get('status')}")
        assert patch_rep.status_code == 200
        assert rep_body["success"] is True
        assert rep_body["data"]["status"] == "RESOLVED_REMOVED"

        # Verify DB directly: report updated and post hidden
        rep_row_post = query_sqlite("SELECT status FROM post_reports WHERE id = ?", (rep_id,))
        post_row_post = query_sqlite("SELECT status FROM posts WHERE id = ?", (target_post_id,))
        print(f"  [4.2 DB POST-STATE] Report status in SQLite: {rep_row_post[0][0]}")
        print(f"  [4.3 DB POST-STATE] Post status in SQLite: {post_row_post[0][0]}")
        assert rep_row_post[0][0] == "RESOLVED_REMOVED"
        assert post_row_post[0][0] == "REPORTED_HIDDEN"

        # Verify GET API
        get_post_api = await client.get("/api/v1/admin/feed/posts?status=REPORTED_HIDDEN")
        assert get_post_api.status_code == 200
        assert any(p["id"] == target_post_id for p in get_post_api.json()["data"])
        print(f"  [4.4 GET API] Verified post listed under status=REPORTED_HIDDEN.")
        print("  -> ACTION 4 EMPIRICALLY CONFIRMED (PASS)")

        # ---------------------------------------------------------------------
        # ACTION 5: PATCH /api/v1/admin/developers/keys/{id}/status
        # ---------------------------------------------------------------------
        print("\n" + "-" * 70)
        print("ACTION 5: PATCH /api/v1/admin/developers/keys/{id}/status")
        print("-" * 70)
        k_id = "key_m1_emp_01"
        key_pre = query_sqlite("SELECT is_active FROM developer_api_keys WHERE id = ?", (k_id,))
        print(f"  [5.0 DB PRE-STATE] Key SQLite is_active: {key_pre[0][0]}")

        # Deactivate Key -> False
        patch_k1 = await client.patch(f"/api/v1/admin/developers/keys/{k_id}/status", json={"is_active": False})
        print(f"  [5.1 MUTATION -> False] HTTP {patch_k1.status_code}")
        k_body1 = patch_k1.json()
        print(f"      Envelope: success={k_body1.get('success')}, timestamp={k_body1.get('timestamp')}")
        print(f"      Returned key data: isActive={k_body1['data'].get('isActive')}, is_active={k_body1['data'].get('is_active')}")
        assert patch_k1.status_code == 200
        assert k_body1["success"] is True
        assert k_body1["data"]["isActive"] is False

        # Verify DB directly
        key_db1 = query_sqlite("SELECT is_active FROM developer_api_keys WHERE id = ?", (k_id,))
        print(f"  [5.2 DB POST-STATE -> False] SQLite is_active: {key_db1[0][0]}")
        assert key_db1[0][0] in (0, False)

        # Reactivate Key -> True
        patch_k2 = await client.patch(f"/api/v1/admin/developers/keys/{k_id}/status", json={"is_active": True})
        print(f"  [5.3 MUTATION -> True] HTTP {patch_k2.status_code}")
        k_body2 = patch_k2.json()
        print(f"      Returned key data: isActive={k_body2['data'].get('isActive')}, is_active={k_body2['data'].get('is_active')}")
        assert patch_k2.status_code == 200
        assert k_body2["data"]["isActive"] is True

        # Verify DB directly
        key_db2 = query_sqlite("SELECT is_active FROM developer_api_keys WHERE id = ?", (k_id,))
        print(f"  [5.4 DB POST-STATE -> True] SQLite is_active: {key_db2[0][0]}")
        assert key_db2[0][0] in (1, True)
        print("  -> ACTION 5 EMPIRICALLY CONFIRMED (PASS)")

        # ---------------------------------------------------------------------
        # ROUTE ALIASES & ERROR RESPONSES
        # ---------------------------------------------------------------------
        print("\n" + "-" * 70)
        print("VERIFICATION: ROUTE ALIASES & ERROR ENVELOPES")
        print("-" * 70)
        alias_res = await client.patch(f"/v1/admin/users/{u_id}/status", json={"is_active": True})
        assert alias_res.status_code == 200
        print("  [ALIAS] /v1/admin mount verified identical to /api/v1/admin.")

        err_404 = await client.patch("/api/v1/admin/users/non_existent_usr/status", json={"is_active": False})
        assert err_404.status_code == 404
        assert err_404.json()["success"] is False
        print(f"  [404 NOT_FOUND] Clean error envelope: {err_404.json()['error']}")

        err_400 = await client.patch(f"/api/v1/admin/users/{u_id}/status", json={"is_active": "INVALID"})
        assert err_400.status_code in (400, 422)
        assert err_400.json()["success"] is False
        print(f"  [400/422 VALIDATION] Clean error envelope: {err_400.json()['error']['code']}")

    # Clean up test DB file
    app.dependency_overrides.pop(get_db, None)
    await test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

    print("\n" + "=" * 80)
    print("ALL 5 FAST ACTIONS AND STATE TRANSITIONS VERIFIED EMPIRICALLY WITH ZERO ERRORS.")
    print("VERDICT: APPROVE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_verification())
