from fastapi import APIRouter

from app.api.v1.admin.overview import router as overview_router
from app.api.v1.admin.users import router as users_router
from app.api.v1.admin.consultations import router as consultations_router
from app.api.v1.admin.library import router as library_router
from app.api.v1.admin.quran import router as quran_router
from app.api.v1.admin.ai import router as ai_router
from app.api.v1.admin.feed import router as feed_router
from app.api.v1.admin.developers import router as developers_router
from app.api.v1.admin.rag_eval import router as rag_eval_router
from app.api.v1.admin.monitoring import router as monitoring_router
from app.api.v1.admin.prayer_times import router as prayer_times_router
from app.api.v1.admin.dhikr import router as dhikr_router

admin_router = APIRouter()

# 1. Overview & System Health
admin_router.include_router(overview_router, tags=["Admin Overview"])
admin_router.include_router(monitoring_router, prefix="/monitoring", tags=["Admin Live Monitoring"])

# 2. Users & Personas
admin_router.include_router(users_router, prefix="/users", tags=["Admin Users"])

# 3. Consultations & Scholars (support both /consultations and /consultation)
admin_router.include_router(consultations_router, prefix="/consultations", tags=["Admin Consultations"])
admin_router.include_router(consultations_router, prefix="/consultation", tags=["Admin Consultations (Alias)"])

# 4. Library & Knowledge Base
admin_router.include_router(library_router, prefix="/library", tags=["Admin Library"])

# 5. Quran & Reciters
admin_router.include_router(quran_router, prefix="/quran", tags=["Admin Quran"])

# 6. AI Chats, Pricing & Sections
admin_router.include_router(ai_router, prefix="/ai", tags=["Admin AI"])

# 7. Feed & Moderation
admin_router.include_router(feed_router, prefix="/feed", tags=["Admin Feed"])

# 8. Developers & System API (support both /developers and /developer)
admin_router.include_router(developers_router, prefix="/developers", tags=["Admin Developers"])
admin_router.include_router(developers_router, prefix="/developer", tags=["Admin Developers (Alias)"])

# 9. RAG Diagnostics & Evaluation Lab
admin_router.include_router(rag_eval_router, prefix="/rag-eval", tags=["Admin RAG Evaluation Lab"])

# 10. Prayer Times & City Management
admin_router.include_router(prayer_times_router, prefix="/prayer-times", tags=["Admin Prayer Times"])

# 11. Dhikr & Supplication Management
admin_router.include_router(dhikr_router, prefix="/dhikr", tags=["Admin Dhikr"])


# System Health alias under /system/health
@admin_router.get("/system/health", tags=["Admin System Health"])
async def system_health_alias(db = None):
    from app.api.v1.admin.developers import get_system_health
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        return await get_system_health(db=session)

__all__ = ["admin_router"]
