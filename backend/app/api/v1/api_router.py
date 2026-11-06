from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.consultation import router as consultation_router
from app.api.v1.library import router as library_router
from app.api.v1.quran import router as quran_router
from app.api.v1.ai import router as ai_router
from app.api.v1.websocket import router as ws_router
from app.api.v1.feed import router as feed_router
from app.api.v1.developer import router as developer_router
from app.api.v1.prayer import router as prayer_router
from app.api.v1.dhikr import router as dhikr_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["۱. احراز هویت و کاربران"])
api_v1_router.include_router(consultation_router, prefix="/consultation", tags=["۲. پاسخ‌کده و مشاوره دینی"])
api_v1_router.include_router(library_router, prefix="/library", tags=["۳. کتابخانه دیجیتال و پژوهش"])
api_v1_router.include_router(quran_router, prefix="/quran", tags=["۴. قرآن کریم و تدبر معارفی"])
api_v1_router.include_router(ai_router, prefix="/ai", tags=["۵. دستیار هوشمند و گفتگوی معارفی"])
api_v1_router.include_router(feed_router, prefix="/feed", tags=["۷. فید و هم‌رسانی محتوا (اینستاگرامی)"])
api_v1_router.include_router(developer_router, prefix="/developer", tags=["۸. پلتفرم توسعه‌دهندگان و API معارفی (Developer Platform)"])
api_v1_router.include_router(prayer_router, prefix="/prayer-times", tags=["۹. اوقات شرعی و موذن"])
api_v1_router.include_router(dhikr_router, prefix="/dhikr", tags=["۱۰. صلوات‌شمار، ادعیه و اذکار"])
api_v1_router.include_router(ws_router, tags=["۶. ارتباط بلادرنگ وب‌سوکت"])



