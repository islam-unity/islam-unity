import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.db.seed_data import seed_database
from app.api.v1.api_router import api_v1_router
from app.api.v1.admin import admin_router
from app.core.middleware import HeaderContextMiddleware
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler
)
from app.core.response import success_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure upload directories exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs("./media", exist_ok=True)
    os.makedirs("./media/ai_exports", exist_ok=True)

    # Initialize tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        from sqlalchemy import text
        if engine.dialect.name == "sqlite":
            for col_def in [
                "ALTER TABLE ai_messages ADD COLUMN sources JSON DEFAULT '[]'",
                "ALTER TABLE ai_messages ADD COLUMN suggest_scholar_escalation BOOLEAN DEFAULT 0",
                "ALTER TABLE ai_messages ADD COLUMN escalation_category VARCHAR(128)",
                "ALTER TABLE ai_messages ADD COLUMN token_usage JSON DEFAULT '{}'",
                "ALTER TABLE users ADD COLUMN age INTEGER",
                "ALTER TABLE users ADD COLUMN gender VARCHAR(16)",
                "ALTER TABLE users ADD COLUMN education VARCHAR(64)",
                "ALTER TABLE users ADD COLUMN interests JSON DEFAULT '[]'",
                "ALTER TABLE users ADD COLUMN knowledge_level VARCHAR(32) DEFAULT 'GENERAL'",
                "ALTER TABLE users ADD COLUMN learning_goals TEXT",
                "ALTER TABLE users ADD COLUMN avatar VARCHAR(256)",
                "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1",
                "ALTER TABLE users ADD COLUMN scholar_status VARCHAR(32) DEFAULT 'NONE'",
                "ALTER TABLE users ADD COLUMN mosque_name VARCHAR(128)",
                "ALTER TABLE users ADD COLUMN mosque_address VARCHAR(256)",
                "ALTER TABLE persona_configs ADD COLUMN bot_name VARCHAR(64) DEFAULT 'دستیار معارفی اتحاد'",
                "ALTER TABLE persona_configs ADD COLUMN bot_role_preset VARCHAR(64) DEFAULT 'GENERAL_ASSISTANT'",
                "ALTER TABLE persona_configs ADD COLUMN bot_avatar VARCHAR(256)",
                "ALTER TABLE scholars ADD COLUMN latitude FLOAT DEFAULT 35.6892",
                "ALTER TABLE scholars ADD COLUMN longitude FLOAT DEFAULT 51.3890",
                "ALTER TABLE scholars ADD COLUMN address VARCHAR(256)",
                "ALTER TABLE scholars ADD COLUMN meeting_slots JSON DEFAULT '[]'",
                "ALTER TABLE books ADD COLUMN topics JSON DEFAULT '[]'",
                "ALTER TABLE consultation_messages ADD COLUMN book_reference JSON",
                "ALTER TABLE ai_conversations ADD COLUMN book_id VARCHAR(64)",
                "ALTER TABLE ai_conversations ADD COLUMN category VARCHAR(128) DEFAULT 'عمومی'",
                "ALTER TABLE ai_messages ADD COLUMN book_page_number INTEGER",
                "ALTER TABLE ai_messages ADD COLUMN book_chapter_id VARCHAR(64)",
                "ALTER TABLE ai_messages ADD COLUMN book_citation TEXT"
            ]:
                try:
                    await conn.execute(text(col_def))
                except Exception:
                    pass

        # Seed default Book AI Categories
        for cat_id, cat_name, cat_desc, cat_icon in [
            ("cat_ai_general", "عمومی و پرسش آزاد", "پرسش‌های عمومی پیرامون محتوا و پیام کتاب", "auto_stories"),
            ("cat_ai_fiqh", "فقه و احکام", "احکام شرعی، فتاوای مذاهب و دلایل فقهی", "balance"),
            ("cat_ai_tafsir", "تفسیر و معارف", "بررسی آیات، شأن نزول و دلالت‌های قرآنی", "menu_book"),
            ("cat_ai_kalam", "کلام و عقاید", "مباحث اعتقادی، توحید و امامت و نبوت", "psychology"),
            ("cat_ai_shobahat", "پاسخ به شبهات", "بررسی ابهامات و نقد دیدگاه‌های معارض", "help_center"),
            ("cat_ai_akhlaq", "اخلاق و سلوک", "پندهای عملی، تهذیب نفس و مکارم اخلاقی", "spa"),
            ("cat_ai_summary", "خلاصه‌سازی و فیش‌برداری", "استخراج پیام‌های کلیدی و چکیده فصل", "summarize")
        ]:
            try:
                if engine.dialect.name == "postgresql":
                    await conn.execute(text(
                        "INSERT INTO book_ai_categories (id, name, description, icon_name, is_system, created_at) "
                        "VALUES (:id, :name, :description, :icon_name, TRUE, CURRENT_TIMESTAMP) "
                        "ON CONFLICT (id) DO NOTHING"
                    ), {"id": cat_id, "name": cat_name, "description": cat_desc, "icon_name": cat_icon})
                else:
                    await conn.execute(text(
                        "INSERT OR IGNORE INTO book_ai_categories (id, name, description, icon_name, is_system, created_at) "
                        "VALUES (:id, :name, :description, :icon_name, 1, CURRENT_TIMESTAMP)"
                    ), {"id": cat_id, "name": cat_name, "description": cat_desc, "icon_name": cat_icon})
            except Exception:
                pass

    # Run initial seed data & sync vector index
    async with AsyncSessionLocal() as session:
        await seed_database(session)
        try:
            from app.services.vector_service import VectorService
            await VectorService.sync_chunks_from_db(session)
        except Exception:
            pass

        try:
            from app.services.prayer_service import PrayerService
            await PrayerService.seed_default_cities(session)
        except Exception:
            pass

        try:
            from app.services.dhikr_service import DhikrService
            await DhikrService.seed_defaults(session)
        except Exception:
            pass

    yield


    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="سند جامع نیازمندی‌های API بک‌اند اپلیکیشن جامع معارفی و هوش مصنوعی «اتحاد»",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Exception Handlers matching Error Matrix
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# Custom Middlewares
app.add_middleware(HeaderContextMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads & media
os.makedirs("./media", exist_ok=True)
app.mount("/media", StaticFiles(directory="./media"), name="media")

# Mount Admin Dashboard Web UI Assets & Routes
_admin_static_candidates = [
    os.path.join(os.path.dirname(__file__), "admin", "static"),
    os.path.abspath("backend/app/admin/static"),
    os.path.abspath("app/admin/static"),
]
ADMIN_STATIC_DIR = os.path.abspath(next((p for p in _admin_static_candidates if os.path.exists(p)), _admin_static_candidates[0]))

if os.path.exists(ADMIN_STATIC_DIR):
    app.mount("/admin/assets", StaticFiles(directory=ADMIN_STATIC_DIR), name="admin_assets")


@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
async def serve_admin_dashboard():
    index_file = os.path.join(ADMIN_STATIC_DIR, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file, media_type="text/html; charset=utf-8")
    return HTMLResponse(
        "<h2 style='text-align:center;font-family:sans-serif;margin-top:50px;'>"
        "فایل‌های پنل مدیریت یافت نشد.</h2>",
        status_code=404
    )


# Mount Admin Router
api_v1_router.include_router(admin_router, prefix="/admin")
app.include_router(admin_router, prefix="/api/v1/admin")
app.include_router(admin_router, prefix="/v1/admin")

# Include API v1 Routers (Both /v1 and /api/v1 for standard compatibility)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)
if settings.API_V1_STR != "/api/v1":
    app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/", summary="سلامت سرور و اطلاعات سرویس")
async def root():
    return success_response({
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "docsUrl": "/docs"
    })


@app.get("/health", summary="بررسی سلامت سیستم (Health Check)")
@app.get("/api/health", summary="بررسی سلامت سیستم (Health Check API)")
@app.get("/api/v1/health", summary="بررسی سلامت سیستم (Health Check v1)")
async def health_check():
    return success_response({
        "status": "healthy"
    })
