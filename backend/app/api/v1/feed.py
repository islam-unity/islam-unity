import os
import uuid
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.db.models import User
from app.config import settings
from app.services.feed_service import FeedService
from app.schemas.feed import (
    CreatePostRequest, CreateCommentRequest, ReportPostRequest,
    AIAssistCaptionRequest
)
from app.core.response import success_response
from app.core.exceptions import AppException

router = APIRouter()


@router.get("", summary="دریافت فید معارفی یکپارچه با فیلترها و مرتب‌سازی")
async def get_feed(
    category: Optional[str] = Query(None, description="ALL, FIQH, AKHLAQ, TAFSIR, AQAED, FAMILY, LIFESTYLE, GENERAL"),
    media_type: Optional[str] = Query(None, description="ALL, VIDEO, AUDIO, IMAGE"),
    scholars_only: bool = Query(False, description="فقط پست‌های عالمان و اساتید تاییدشده"),
    madhhab: Optional[str] = Query(None, description="همه، شیعه اثناعشری، اهل سنت حنفی، اهل سنت شافعی"),
    search: Optional[str] = Query(None, description="جستجوی متنی در عنوان و کپشن پست"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    result = await FeedService.get_feed(
        db=db,
        current_user_id=user_id,
        category=category,
        media_type=media_type,
        scholars_only=scholars_only,
        madhhab=madhhab,
        search=search,
        page=page,
        limit=limit
    )
    return success_response(
        data=result.model_dump(),
        meta={"page": result.page, "limit": result.limit, "total": result.total, "has_more": result.has_more}
    )


@router.get("/metadata", summary="متادیتای فیلترهای فید معارفی")
async def get_feed_metadata():
    categories = [
        {"id": "ALL", "title": "همه موضوعات", "icon": "category"},
        {"id": "FIQH", "title": "احکام و فقه", "icon": "balance"},
        {"id": "AKHLAQ", "title": "اخلاق و تربیت", "icon": "spa"},
        {"id": "TAFSIR", "title": "تفسیر و تدبر", "icon": "menu_book"},
        {"id": "AQAED", "title": "عقاید و کلام", "icon": "psychology"},
        {"id": "FAMILY", "title": "خانواده و جوانان", "icon": "family_restroom"},
        {"id": "LIFESTYLE", "title": "سبک زندگی", "icon": "favorite"}
    ]
    media_types = [
        {"id": "ALL", "title": "همه رسانه‌ها", "icon": "apps"},
        {"id": "VIDEO", "title": "ویدیو و ریلز", "icon": "smart_display"},
        {"id": "AUDIO", "title": "پادکست و صوت", "icon": "headphones"},
        {"id": "IMAGE", "title": "تصاویر و اینفوگرافیک", "icon": "photo_library"}
    ]
    madhhabs = [
        "همه", "مشترک", "شیعه اثناعشری", "اهل سنت حنفی", "اهل سنت شافعی"
    ]
    return success_response(data={
        "categories": categories,
        "media_types": media_types,
        "madhhabs": madhhabs
    })


@router.get("/profile/{user_id}", summary="پروفایل اینستاگرامی ناشر (عالمان و مردم) با گرید پست‌ها")
async def get_author_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    viewer_id = current_user.id if current_user else None
    profile = await FeedService.get_author_profile(db, user_id, viewer_id)
    return success_response(data=profile.model_dump())


@router.get("/{post_id}", summary="دریافت جزئیات کامل یک پست معارفی")
async def get_post_detail(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    post = await FeedService.get_post_by_id(db, post_id, user_id)
    return success_response(data=post.model_dump())


@router.post("", summary="ایجاد و انتشار پست جدید معارفی (هم مردم و هم عالمان)")
async def create_post(
    data: CreatePostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = await FeedService.create_post(db, current_user, data)
    return success_response(data=post.model_dump())


@router.post("/{post_id}/like", summary="لایک یا برداشتن لایک پست")
async def toggle_like(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await FeedService.toggle_like(db, post_id, current_user.id)
    return success_response(data=res)


@router.post("/{post_id}/bookmark", summary="ذخیره یا حذف پست از نشان‌شده‌ها (Bookmarks)")
async def toggle_bookmark(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await FeedService.toggle_bookmark(db, post_id, current_user.id)
    return success_response(data=res)


@router.get("/{post_id}/comments", summary="دریافت نظرات و پاسخ‌های یک پست")
async def get_comments(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    user_id = current_user.id if current_user else None
    comments = await FeedService.get_comments(db, post_id, user_id)
    return success_response(data=[c.model_dump() for c in comments])


@router.post("/{post_id}/comments", summary="ثبت نظر یا پاسخ به نظر برای پست")
async def add_comment(
    post_id: str,
    data: CreateCommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = await FeedService.add_comment(db, post_id, current_user, data)
    return success_response(data=comment.model_dump())


@router.post("/{post_id}/comments/{comment_id}/pin", summary="پین یا آن‌پین کردن پاسخ فقهی/معارفی استاد")
async def pin_comment(
    post_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await FeedService.pin_comment(db, post_id, comment_id, current_user)
    return success_response(data=res)


@router.post("/{post_id}/report", summary="گزارش تخلف یا محتوای نامناسب پست")
async def report_post(
    post_id: str,
    data: ReportPostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res = await FeedService.report_post(db, post_id, current_user.id, data)
    return success_response(data=res)


@router.post("/ai/assist-caption", summary="دستیار هوش مصنوعی برای بهبود کپشن و پیشنهاد هشتگ‌ها و آیات")
async def ai_assist_caption(
    data: AIAssistCaptionRequest
):
    res = await FeedService.ai_assist_caption(data)
    return success_response(data=res.model_dump())


@router.get("/{post_id}/ai-analyze", summary="تحلیل معارفی و استخراج مضامین قرآنی/روایی پست توسط هوش مصنوعی")
async def ai_analyze_post(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    res = await FeedService.ai_analyze_post(db, post_id)
    return success_response(data=res.model_dump())


@router.post("/upload", summary="بارگذاری فایل چندرسانه‌ای (عکس، ویدیو، صوت)")
async def upload_media_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Determine type
    content_type = file.content_type or ""
    if content_type.startswith("image/"):
        m_type = "IMAGE"
    elif content_type.startswith("video/"):
        m_type = "VIDEO"
    elif content_type.startswith("audio/"):
        m_type = "AUDIO"
    else:
        m_type = "IMAGE"

    upload_folder = os.path.join(settings.UPLOAD_DIR, "posts")
    os.makedirs(upload_folder, exist_ok=True)

    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    safe_filename = f"{m_type.lower()}_{uuid.uuid4().hex[:12]}{ext}"
    target_path = os.path.join(upload_folder, safe_filename)

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media_url = f"{settings.STATIC_URL_PREFIX}/uploads/posts/{safe_filename}"
    return success_response(data={
        "media_url": media_url,
        "media_type": m_type,
        "file_name": safe_filename,
        "original_name": file.filename
    })
