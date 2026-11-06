import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.db.seed_data import seed_database
from app.db.models import (
    User, PersonaConfig, Scholar, ConsultationThread, ConsultationMessage, ConsultationAttachment,
    LibraryCategory, Book, BookChapter, KnowledgeChunk, ReadingProgress,
    Surah, Ayah, AyahTadabburData, Reciter, AudioSegment,
    AIConversation, AIMessage, AIUsageLog, AIModelPricing, AISectionConfig,
    Post, PostReport, DeveloperAccount, DeveloperApiKey
)

TEST_DB_FILE = "./test_admin_api_isolated.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

test_engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# IMPORTANT: Shadow conftest.py setup_test_db to protect ./ettehad.db
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    pass

@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_admin_api_db():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    app.dependency_overrides[get_db] = override_get_db

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        await seed_database(session)

        # Supplemental records for complete 8-domain testing
        urgent_th = ConsultationThread(
            id="thread_urgent_01",
            user_id="usr_seeker_1",
            target_scholar_id="scholar_1",
            title="پرسش فوری فقهی در خصوص سفر اضطراری",
            category="احکام شرعی و فقهی",
            tracking_code="ETH-Q-URGENT-99",
            status="WAITING_SCHOLAR",
            is_anonymous=False,
            is_public=True,
            is_urgent=True,
            is_bookmarked=False,
            created_at=datetime.now(timezone.utc)
        )
        session.add(urgent_th)

        chunk = KnowledgeChunk(
            id="chnk_api_01", book_id="book_nahj", chapter_id="chap_nahj_1", chunk_order=1,
            full_text="سرآغاز دین معرفت اوست و کمال معرفتش تصدیق اوست.", text_arabic="أَوَّلُ الدِّينِ مَعْرِفَتُهُ",
            summary="مفهوم توحید و کمال دین در خطبه نخست نهج البلاغه", core_concepts=["توحید", "معرفت الله"],
            hypothetical_questions=["سرآغاز دین چیست؟"], page_number=15, is_processed=True,
            created_at=datetime.now(timezone.utc)
        )
        session.add(chunk)

        prog = ReadingProgress(
            user_id="usr_seeker_1", book_id="book_nahj", current_chapter_id="chap_nahj_1",
            current_paragraph_index=0, percentage=25.0, updated_at=datetime.now(timezone.utc)
        )
        session.add(prog)

        conv = AIConversation(
            id="conv_api_01", user_id="usr_seeker_1", title="پرسش پیرامون وحدت اسلامی",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
        )
        session.add(conv)
        msg1 = AIMessage(
            id="msg_api_01", conversation_id="conv_api_01", role="user",
            content="دیدگاه فریقین چیست؟", created_at=datetime.now(timezone.utc)
        )
        session.add(msg1)

        log = AIUsageLog(
            id="log_api_01", user_id="usr_seeker_1", conversation_id="conv_api_01", message_id="msg_api_01",
            model_name="gemini-1.5-pro", prompt_tokens=100, output_tokens=50, total_tokens=150,
            cost_usd=0.0003, cost_irr=285.0, exchange_rate_applied=950000.0, created_at=datetime.now(timezone.utc)
        )
        session.add(log)

        p1 = AIModelPricing(
            id="gemini-1.5-pro", model_name="gemini-1.5-pro", input_cost_per_million_usd=1.25,
            output_cost_per_million_usd=5.00, cached_cost_per_million_usd=0.30, is_active=True,
            updated_at=datetime.now(timezone.utc)
        )
        session.add(p1)

        rep = PostReport(
            id="rep_api_01", post_id="post_fiqh_crypto_01", user_id="usr_seeker_1",
            reason="MISLEADING_CONTENT", description="نیاز به بررسی در کارتابل نظارت",
            status="PENDING", created_at=datetime.now(timezone.utc)
        )
        session.add(rep)

        dev_acc = DeveloperAccount(
            id="dev_acc_api_01", user_id="usr_seeker_1", app_name="اپلیکیشن تست معارفی",
            description="سرویس توسعه‌دهنده جهت تست API", tier="STANDARD", monthly_quota_tokens=1000000,
            used_tokens_this_month=5000, rate_limit_per_minute=60, is_active=True, created_at=datetime.now(timezone.utc)
        )
        session.add(dev_acc)
        dev_key = DeveloperApiKey(
            id="key_api_01", account_id="dev_acc_api_01", key_hash="hash_api_key_test_123",
            key_prefix="ett_api_99", label="کلید تستی ادمین", is_active=True,
            total_requests=10, total_tokens=1500, created_at=datetime.now(timezone.utc)
        )
        session.add(dev_key)

        await session.commit()

    yield

    app.dependency_overrides.pop(get_db, None)
    await test_engine.dispose()
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

@pytest_asyncio.fixture
async def api_client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# =========================================================================
# TIER 1: 8 Domain Test Functions (Core CRUD & Listing)
# =========================================================================

@pytest.mark.asyncio
async def test_tier1_overview_kpis(api_client: httpx.AsyncClient):
    """F1: Overview & Analytics KPI metrics and system health status."""
    resp = await api_client.get("/api/v1/admin/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    assert "totalUsers" in data and data["totalUsers"] >= 1
    assert "totalScholars" in data and data["totalScholars"] >= 1
    assert "openThreads" in data and data["openThreads"] >= 1
    assert "aiTokensConsumed" in data and data["aiTokensConsumed"] >= 150
    assert "contentReportsCount" in data and data["contentReportsCount"] >= 1
    assert "systemHealth" in data
    assert data["systemHealth"]["status"] == "healthy"
    assert data["systemHealth"]["database"] == "connected"


@pytest.mark.asyncio
async def test_tier1_users_list_and_detail(api_client: httpx.AsyncClient):
    """F2: Users & Personas listing and profile/persona inspection."""
    resp = await api_client.get("/api/v1/admin/users?page=1&pageSize=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["data"]) > 0

    first_user = body["data"][0]
    user_id = first_user["id"]

    detail_resp = await api_client.get(f"/api/v1/admin/users/{user_id}")
    assert detail_resp.status_code == 200
    detail_body = detail_resp.json()
    assert detail_body["success"] is True
    assert detail_body["data"]["id"] == user_id
    assert "phoneNumber" in detail_body["data"]
    assert "role" in detail_body["data"]
    assert "persona" in detail_body["data"]


@pytest.mark.asyncio
async def test_tier1_consultations_scholars_and_threads(api_client: httpx.AsyncClient):
    """F3: Consultations & Scholars list, threads pagination and thread detail."""
    resp_scholars = await api_client.get("/api/v1/admin/consultations/scholars")
    assert resp_scholars.status_code == 200
    body_scholars = resp_scholars.json()
    assert body_scholars["success"] is True
    assert len(body_scholars["data"]) > 0

    resp_threads = await api_client.get("/api/v1/admin/consultations/threads?page=1&pageSize=10")
    assert resp_threads.status_code == 200
    body_threads = resp_threads.json()
    assert body_threads["success"] is True
    assert len(body_threads["data"]) > 0

    thread_id = body_threads["data"][0]["id"]
    resp_thread = await api_client.get(f"/api/v1/admin/consultations/threads/{thread_id}")
    assert resp_thread.status_code == 200
    body_thread = resp_thread.json()
    assert body_thread["success"] is True
    assert body_thread["data"]["id"] == thread_id
    assert "messages" in body_thread["data"]
    assert "attachments" in body_thread["data"]


@pytest.mark.asyncio
async def test_tier1_library_categories_books_chunks(api_client: httpx.AsyncClient):
    """F4: Library categories, books, chapters, knowledge chunks and reading stats."""
    resp_cats = await api_client.get("/api/v1/admin/library/categories")
    assert resp_cats.status_code == 200
    assert resp_cats.json()["success"] is True
    assert len(resp_cats.json()["data"]) > 0

    resp_books = await api_client.get("/api/v1/admin/library/books")
    assert resp_books.status_code == 200
    assert resp_books.json()["success"] is True
    assert len(resp_books.json()["data"]) > 0

    resp_chaps = await api_client.get("/api/v1/admin/library/books/book_nahj/chapters")
    assert resp_chaps.status_code == 200
    assert resp_chaps.json()["success"] is True
    assert len(resp_chaps.json()["data"]) > 0

    resp_chunks = await api_client.get("/api/v1/admin/library/chunks?book_id=book_nahj")
    assert resp_chunks.status_code == 200
    body_chunks = resp_chunks.json()
    assert body_chunks["success"] is True
    assert any(c["id"] == "chnk_api_01" for c in body_chunks["data"])

    resp_prog = await api_client.get("/api/v1/admin/library/reading-progress")
    assert resp_prog.status_code == 200
    assert resp_prog.json()["success"] is True
    assert len(resp_prog.json()["data"]) > 0


@pytest.mark.asyncio
async def test_tier1_quran_surahs_ayahs_reciters(api_client: httpx.AsyncClient):
    """F5: Quran surahs, ayahs pagination, tadabbur commentary and reciters."""
    resp_surahs = await api_client.get("/api/v1/admin/quran/surahs?page=1&pageSize=10")
    assert resp_surahs.status_code == 200
    assert resp_surahs.json()["success"] is True
    assert len(resp_surahs.json()["data"]) > 0

    resp_ayahs = await api_client.get("/api/v1/admin/quran/ayahs?page=1&pageSize=10")
    assert resp_ayahs.status_code == 200
    assert resp_ayahs.json()["success"] is True
    assert len(resp_ayahs.json()["data"]) > 0

    resp_tadabbur = await api_client.get("/api/v1/admin/quran/ayahs/49/10/tadabbur")
    assert resp_tadabbur.status_code == 200
    body_tadabbur = resp_tadabbur.json()
    assert body_tadabbur["success"] is True
    assert "briefTafsir" in body_tadabbur["data"] or "brief_tafsir" in body_tadabbur["data"]

    resp_reciters = await api_client.get("/api/v1/admin/quran/reciters")
    assert resp_reciters.status_code == 200
    assert resp_reciters.json()["success"] is True
    assert len(resp_reciters.json()["data"]) > 0


@pytest.mark.asyncio
async def test_tier1_ai_conversations_logs_pricing_sections(api_client: httpx.AsyncClient):
    """F6: AI conversations, message history, usage logs, model pricing and sections."""
    resp_convs = await api_client.get("/api/v1/admin/ai/conversations")
    assert resp_convs.status_code == 200
    assert resp_convs.json()["success"] is True
    assert len(resp_convs.json()["data"]) > 0

    resp_msgs = await api_client.get("/api/v1/admin/ai/conversations/conv_api_01/messages")
    assert resp_msgs.status_code == 200
    body_msgs = resp_msgs.json()
    assert body_msgs["success"] is True
    assert len(body_msgs["data"]) > 0
    assert body_msgs["data"][0]["id"] == "msg_api_01"

    resp_logs = await api_client.get("/api/v1/admin/ai/usage-logs")
    assert resp_logs.status_code == 200
    assert resp_logs.json()["success"] is True
    assert len(resp_logs.json()["data"]) > 0

    resp_pricing = await api_client.get("/api/v1/admin/ai/model-pricing")
    assert resp_pricing.status_code == 200
    body_pricing = resp_pricing.json()
    assert body_pricing["success"] is True
    assert any(p["id"] == "gemini-1.5-pro" for p in body_pricing["data"])

    resp_sections = await api_client.get("/api/v1/admin/ai/sections")
    assert resp_sections.status_code == 200
    assert resp_sections.json()["success"] is True
    assert len(resp_sections.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_tier1_feed_posts_and_reports(api_client: httpx.AsyncClient):
    """F7: Social feed posts and content reports listing."""
    resp_posts = await api_client.get("/api/v1/admin/feed/posts")
    assert resp_posts.status_code == 200
    assert resp_posts.json()["success"] is True
    assert len(resp_posts.json()["data"]) > 0

    resp_reports = await api_client.get("/api/v1/admin/feed/reports")
    assert resp_reports.status_code == 200
    body_reports = resp_reports.json()
    assert body_reports["success"] is True
    assert any(r["id"] == "rep_api_01" for r in body_reports["data"])


@pytest.mark.asyncio
async def test_tier1_developers_accounts_keys_health(api_client: httpx.AsyncClient):
    """F8: Developer accounts, API keys and system health report."""
    resp_accounts = await api_client.get("/api/v1/admin/developers/accounts")
    assert resp_accounts.status_code == 200
    assert resp_accounts.json()["success"] is True
    assert len(resp_accounts.json()["data"]) > 0

    resp_keys = await api_client.get("/api/v1/admin/developers/keys")
    assert resp_keys.status_code == 200
    assert resp_keys.json()["success"] is True
    assert any(k["id"] == "key_api_01" for k in resp_keys.json()["data"])

    resp_health = await api_client.get("/api/v1/admin/developers/system-health")
    assert resp_health.status_code == 200
    body_health = resp_health.json()
    assert body_health["success"] is True
    assert body_health["data"]["status"] == "healthy"
    assert body_health["data"]["database"]["status"] == "connected"


# =========================================================================
# TIER 2: Boundary & Corner Cases
# =========================================================================

@pytest.mark.asyncio
async def test_tier2_non_existent_resources_404(api_client: httpx.AsyncClient):
    """Verify 404 responses for nonexistent user, thread, chunk, and pricing resources."""
    r_user = await api_client.get("/api/v1/admin/users/usr_non_existent_9999")
    assert r_user.status_code == 404
    assert r_user.json()["success"] is False

    r_thread = await api_client.get("/api/v1/admin/consultations/threads/th_non_existent_9999")
    assert r_thread.status_code == 404
    assert r_thread.json()["success"] is False

    r_book = await api_client.get("/api/v1/admin/library/books/book_non_existent_9999/chapters")
    assert r_book.status_code == 404
    assert r_book.json()["success"] is False

    r_tadabbur = await api_client.get("/api/v1/admin/quran/ayahs/999/999/tadabbur")
    assert r_tadabbur.status_code == 404
    assert r_tadabbur.json()["success"] is False

    r_conv = await api_client.get("/api/v1/admin/ai/conversations/conv_non_existent_9999/messages")
    assert r_conv.status_code == 404
    assert r_conv.json()["success"] is False

    r_price = await api_client.put(
        "/api/v1/admin/ai/model-pricing/model_non_existent_9999",
        json={"input_cost_per_million_usd": 1.0}
    )
    assert r_price.status_code == 404
    assert r_price.json()["success"] is False

    r_rep = await api_client.patch(
        "/api/v1/admin/feed/reports/rep_non_existent_9999/status",
        json={"status": "RESOLVED_DISMISSED"}
    )
    assert r_rep.status_code == 404
    assert r_rep.json()["success"] is False

    r_key = await api_client.patch(
        "/api/v1/admin/developers/keys/key_non_existent_9999/status",
        json={"is_active": False}
    )
    assert r_key.status_code == 404
    assert r_key.json()["success"] is False


@pytest.mark.asyncio
async def test_tier2_out_of_bounds_pagination(api_client: httpx.AsyncClient):
    """Verify out-of-bounds page numbers return data=[], totalCount>0, and hasMore=False."""
    resp = await api_client.get("/api/v1/admin/users?page=99999&pageSize=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] == []
    assert body["meta"]["page"] == 99999
    assert body["meta"]["totalCount"] > 0
    assert body["meta"]["hasMore"] is False

    resp_ayahs = await api_client.get("/api/v1/admin/quran/ayahs?page=99999&pageSize=20")
    assert resp_ayahs.status_code == 200
    body_ayahs = resp_ayahs.json()
    assert body_ayahs["success"] is True
    assert body_ayahs["data"] == []
    assert body_ayahs["meta"]["hasMore"] is False
    assert body_ayahs["meta"]["totalCount"] > 0


@pytest.mark.asyncio
async def test_tier2_empty_and_special_char_search(api_client: httpx.AsyncClient):
    """Verify empty strings, wildcards, SQL injection tokens, and Unicode return 200 without 500 error."""
    r_empty = await api_client.get("/api/v1/admin/users?search=")
    assert r_empty.status_code == 200
    assert r_empty.json()["success"] is True

    r_wild = await api_client.get("/api/v1/admin/users?search=%25%25_")
    assert r_wild.status_code == 200
    assert r_wild.json()["success"] is True

    r_inj = await api_client.get("/api/v1/admin/feed/posts?search=' OR '1'='1")
    assert r_inj.status_code == 200
    assert r_inj.json()["success"] is True

    r_emoji = await api_client.get("/api/v1/admin/library/chunks?search=🚀🔥✨")
    assert r_emoji.status_code == 200
    assert r_emoji.json()["success"] is True

    r_zwnj = await api_client.get("/api/v1/admin/quran/ayahs?search=می‌شود")
    assert r_zwnj.status_code == 200
    assert r_zwnj.json()["success"] is True


@pytest.mark.asyncio
async def test_tier2_invalid_payload_returns_422(api_client: httpx.AsyncClient):
    """Verify invalid types in PATCH or POST bodies produce validation rejection (HTTP 400 or 422)."""
    r1 = await api_client.patch(
        "/api/v1/admin/users/usr_seeker_1/status",
        json={"is_active": ["invalid_array"]}
    )
    assert r1.status_code in (400, 422)
    assert r1.json()["success"] is False

    r2 = await api_client.patch(
        "/api/v1/admin/developers/keys/key_api_01/status",
        json={"is_active": {"dict": "invalid"}}
    )
    assert r2.status_code in (400, 422)
    assert r2.json()["success"] is False

    r3 = await api_client.post(
        "/api/v1/admin/consultations/threads/thread_839210/reply",
        json={}
    )
    assert r3.status_code in (400, 422)
    assert r3.json()["success"] is False

    r4 = await api_client.put(
        "/api/v1/admin/ai/model-pricing/gemini-1.5-pro",
        json={"input_cost_per_million_usd": "not_a_number"}
    )
    assert r4.status_code in (400, 422)
    assert r4.json()["success"] is False


# =========================================================================
# TIER 3: Combinatorial & Envelope Integrity
# =========================================================================

@pytest.mark.asyncio
async def test_tier3_standard_response_envelope(api_client: httpx.AsyncClient):
    """Verify success==True, ISO timestamp, and all 7 meta fields in standard envelope."""
    resp = await api_client.get("/api/v1/admin/users?page=1&pageSize=5")
    assert resp.status_code == 200
    body = resp.json()

    assert body["success"] is True
    assert "data" in body
    assert "timestamp" in body
    assert "meta" in body

    meta = body["meta"]
    assert meta["page"] == 1
    assert meta["pageSize"] == 5
    assert meta["limit"] == 5
    assert isinstance(meta["totalCount"], int) and meta["totalCount"] >= 1
    assert isinstance(meta["total"], int) and meta["total"] >= 1
    assert isinstance(meta["totalPages"], int) and meta["totalPages"] >= 1
    assert isinstance(meta["hasMore"], bool)

    # Test error envelope conforms as well
    err_resp = await api_client.get("/api/v1/admin/users/usr_unknown_envelope_test")
    assert err_resp.status_code == 404
    err_body = err_resp.json()
    assert err_body["success"] is False
    assert "error" in err_body
    assert "timestamp" in err_body


@pytest.mark.asyncio
async def test_tier3_sorting_functionality(api_client: httpx.AsyncClient):
    """Verify sortBy and sortOrder (asc/desc) functionality."""
    r_asc = await api_client.get("/api/v1/admin/users?sortBy=id&sortOrder=asc&pageSize=50")
    assert r_asc.status_code == 200
    ids_asc = [u["id"] for u in r_asc.json()["data"]]

    r_desc = await api_client.get("/api/v1/admin/users?sortBy=id&sortOrder=desc&pageSize=50")
    assert r_desc.status_code == 200
    ids_desc = [u["id"] for u in r_desc.json()["data"]]

    assert ids_asc == sorted(ids_asc)
    assert ids_desc == sorted(ids_desc, reverse=True)

    r_th_asc = await api_client.get("/api/v1/admin/consultations/threads?sortBy=title&sortOrder=asc")
    assert r_th_asc.status_code == 200
    r_th_desc = await api_client.get("/api/v1/admin/consultations/threads?sortBy=title&sortOrder=desc")
    assert r_th_desc.status_code == 200


@pytest.mark.asyncio
async def test_tier3_multi_filter_combinations(api_client: httpx.AsyncClient):
    """Verify combinations of search + role, is_urgent + status, and category_id + search."""
    r_users = await api_client.get("/api/v1/admin/users?role=SEEKER&is_active=true")
    assert r_users.status_code == 200
    for u in r_users.json()["data"]:
        assert u["role"] == "SEEKER"
        assert u["isActive"] is True

    r_threads = await api_client.get("/api/v1/admin/consultations/threads?is_urgent=true&status=WAITING_SCHOLAR")
    assert r_threads.status_code == 200
    assert len(r_threads.json()["data"]) >= 1
    for t in r_threads.json()["data"]:
        assert t["isUrgent"] is True
        assert t["status"] == "WAITING_SCHOLAR"

    r_books = await api_client.get("/api/v1/admin/library/books?category_id=cat_hadith&search=نهج")
    assert r_books.status_code == 200
    for b in r_books.json()["data"]:
        assert b["categoryId"] == "cat_hadith"


@pytest.mark.asyncio
async def test_tier3_dual_route_aliases(api_client: httpx.AsyncClient):
    """Verify dual route mounts: /api/v1/admin/... and /v1/admin/... as well as singular aliases."""
    r1 = await api_client.get("/api/v1/admin/overview")
    r2 = await api_client.get("/v1/admin/overview")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["data"]["totalUsers"] == r2.json()["data"]["totalUsers"]

    r_users1 = await api_client.get("/api/v1/admin/users")
    r_users2 = await api_client.get("/v1/admin/users")
    assert r_users1.status_code == 200
    assert r_users2.status_code == 200

    r_cons1 = await api_client.get("/api/v1/admin/consultations/threads")
    r_cons2 = await api_client.get("/api/v1/admin/consultation/threads")
    assert r_cons1.status_code == 200
    assert r_cons2.status_code == 200

    r_dev1 = await api_client.get("/api/v1/admin/developers/accounts")
    r_dev2 = await api_client.get("/api/v1/admin/developer/accounts")
    assert r_dev1.status_code == 200
    assert r_dev2.status_code == 200

    r_health = await api_client.get("/api/v1/admin/developers/system-health")
    assert r_health.status_code == 200
    assert r_health.json()["data"]["status"] == "healthy"


# =========================================================================
# TIER 4: Real-World Scenarios
# =========================================================================

@pytest.mark.asyncio
async def test_tier4_content_moderation_lifecycle(api_client: httpx.AsyncClient):
    """Scenario 1: Report RESOLVED_REMOVED automatically transitions flagged post to REPORTED_HIDDEN."""
    r_rep = await api_client.get("/api/v1/admin/feed/reports?status=PENDING")
    assert r_rep.status_code == 200
    pending_reps = [r for r in r_rep.json()["data"] if r["id"] == "rep_api_01"]
    assert len(pending_reps) > 0

    r_post = await api_client.get("/api/v1/admin/feed/posts?search=رمزارزها")
    assert r_post.status_code == 200
    post_item = next((p for p in r_post.json()["data"] if p["id"] == "post_fiqh_crypto_01"), None)
    assert post_item is not None
    assert post_item["status"] != "REPORTED_HIDDEN"

    # Resolve report by removing content
    r_action = await api_client.patch(
        "/api/v1/admin/feed/reports/rep_api_01/status",
        json={"status": "RESOLVED_REMOVED"}
    )
    assert r_action.status_code == 200
    assert r_action.json()["data"]["status"] == "RESOLVED_REMOVED"

    # Verify post status updated to REPORTED_HIDDEN
    r_post_after = await api_client.get("/api/v1/admin/feed/posts?status=REPORTED_HIDDEN")
    assert r_post_after.status_code == 200
    hidden_post = next((p for p in r_post_after.json()["data"] if p["id"] == "post_fiqh_crypto_01"), None)
    assert hidden_post is not None
    assert hidden_post["status"] == "REPORTED_HIDDEN"


@pytest.mark.asyncio
async def test_tier4_urgent_consultation_quick_reply(api_client: httpx.AsyncClient):
    """Scenario 2: Quick reply to consultation thread adds message and marks thread ANSWERED."""
    thread_id = "thread_urgent_01"
    r_detail_before = await api_client.get(f"/api/v1/admin/consultations/threads/{thread_id}")
    assert r_detail_before.status_code == 200
    initial_count = len(r_detail_before.json()["data"]["messages"])
    assert r_detail_before.json()["data"]["status"] == "WAITING_SCHOLAR"

    # Send quick reply
    r_reply = await api_client.post(
        f"/api/v1/admin/consultations/threads/{thread_id}/reply",
        json={
            "text": "پاسخ فوری به سوال شرعی: در سفر اضطراری نماز طبق موازین شکسته است.",
            "sender_role": "SCHOLAR",
            "citation": "تحریر الوسیله، باب صلاة المسافر"
        }
    )
    assert r_reply.status_code == 200
    reply_body = r_reply.json()
    assert reply_body["success"] is True
    assert reply_body["data"]["text"] == "پاسخ فوری به سوال شرعی: در سفر اضطراری نماز طبق موازین شکسته است."
    assert reply_body["data"]["senderRole"] == "SCHOLAR"

    # Inspect thread detail after reply
    r_detail_after = await api_client.get(f"/api/v1/admin/consultations/threads/{thread_id}")
    assert r_detail_after.status_code == 200
    after_data = r_detail_after.json()["data"]
    assert after_data["status"] == "ANSWERED"
    assert len(after_data["messages"]) == initial_count + 1


@pytest.mark.asyncio
async def test_tier4_developer_key_lifecycle(api_client: httpx.AsyncClient):
    """Scenario 3: Toggle developer API key status False -> True and verify list filtering."""
    key_id = "key_api_01"
    # Deactivate key
    r_deact = await api_client.patch(
        f"/api/v1/admin/developers/keys/{key_id}/status",
        json={"is_active": False}
    )
    assert r_deact.status_code == 200
    assert r_deact.json()["data"]["isActive"] is False

    # Verify key in inactive query
    r_inactive = await api_client.get("/api/v1/admin/developers/keys?is_active=false")
    assert r_inactive.status_code == 200
    assert any(k["id"] == key_id for k in r_inactive.json()["data"])

    # Reactivate key
    r_react = await api_client.patch(
        f"/api/v1/admin/developers/keys/{key_id}/status",
        json={"is_active": True}
    )
    assert r_react.status_code == 200
    assert r_react.json()["data"]["isActive"] is True


@pytest.mark.asyncio
async def test_tier4_ai_model_pricing_update(api_client: httpx.AsyncClient):
    """Scenario 4: Update AI model token pricing tariffs and verify persistence."""
    model_id = "gemini-1.5-pro"
    # Update pricing tariff
    r_update = await api_client.put(
        f"/api/v1/admin/ai/model-pricing/{model_id}",
        json={
            "input_cost_per_million_usd": 1.75,
            "output_cost_per_million_usd": 7.00,
            "cached_cost_per_million_usd": 0.45,
            "is_active": True
        }
    )
    assert r_update.status_code == 200
    updated_data = r_update.json()["data"]
    assert updated_data["inputCostPerMillionUsd"] == 1.75
    assert updated_data["outputCostPerMillionUsd"] == 7.00
    assert updated_data["cachedCostPerMillionUsd"] == 0.45

    # Verify persistence via GET
    r_get = await api_client.get("/api/v1/admin/ai/model-pricing")
    assert r_get.status_code == 200
    target_pricing = next((p for p in r_get.json()["data"] if p["id"] == model_id), None)
    assert target_pricing is not None
    assert target_pricing["inputCostPerMillionUsd"] == 1.75
    assert target_pricing["outputCostPerMillionUsd"] == 7.00


@pytest.mark.asyncio
async def test_tier4_user_status_toggle(api_client: httpx.AsyncClient):
    """Scenario 5: User active status toggle True -> False -> True."""
    user_id = "usr_seeker_1"
    # Verify initially active
    r_init = await api_client.get(f"/api/v1/admin/users/{user_id}")
    assert r_init.status_code == 200
    assert r_init.json()["data"]["isActive"] is True

    # Deactivate user
    r_deact = await api_client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": False}
    )
    assert r_deact.status_code == 200
    assert r_deact.json()["data"]["isActive"] is False

    # Verify deactivation persisted
    r_check_deact = await api_client.get(f"/api/v1/admin/users/{user_id}")
    assert r_check_deact.status_code == 200
    assert r_check_deact.json()["data"]["isActive"] is False

    # Reactivate user
    r_react = await api_client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        json={"is_active": True}
    )
    assert r_react.status_code == 200
    assert r_react.json()["data"]["isActive"] is True

    # Verify reactivation persisted
    r_check_react = await api_client.get(f"/api/v1/admin/users/{user_id}")
    assert r_check_react.status_code == 200
    assert r_check_react.json()["data"]["isActive"] is True
