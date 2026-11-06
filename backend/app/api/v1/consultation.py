import os
import uuid
import shutil
from typing import Optional, Any, List, Dict
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_scholar
from app.db.models import User
from app.config import settings
from app.services.consultation_service import ConsultationService
from app.schemas.consultation import (
    CreateThreadRequest, CreateMessageRequest,
    UpdateThreadStatusRequest, UpdateThreadVisibilityRequest,
    CreateQuickReplyRequest
)
from app.core.response import success_response
from app.core.exceptions import AttachmentOversizeException

router = APIRouter()


# 2.1 Scholars Directory
@router.get("/scholars", summary="فهرست اساتید و علما با فیلترهای پیشرفته")
async def get_scholars(
    q: Optional[str] = Query(None, description="عبارت جستجو در نام، تخصص یا بیو"),
    madhhab: Optional[str] = Query(None, description="شیعه اثناعشری، اهل سنت (حنفی)، اهل سنت (شافعی)"),
    city: Optional[str] = Query(None, description="قم، مشهد، تهران، سنندج و..."),
    mosque: Optional[str] = Query(None, description="نام مرکز فقهی، حرم مطهر یا دارالافتاء"),
    specialty: Optional[str] = Query(None, description="احکام شرعی، اعتقادی، مشاوره، تفسیر..."),
    minRating: Optional[float] = Query(None, description="حداقل امتیاز"),
    sort: Optional[str] = Query("RANK_RATING", description="RANK_RATING, ANSWERS_COUNT, RESPONSE_SPEED"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await ConsultationService.get_scholars(
        db=db,
        q=q,
        madhhab=madhhab,
        city=city,
        mosque=mosque,
        specialty=specialty,
        min_rating=minRating,
        sort=sort,
        page=page,
        limit=limit
    )
    return success_response(
        data=[s.model_dump() for s in result["items"]],
        meta=result["meta"]
    )


@router.get("/scholars/metadata", summary="متادیتای فیلترهای علما (شهرها، مساجد، مذاهب، تخصص‌ها)")
async def get_scholars_metadata(
    db: AsyncSession = Depends(get_db)
):
    metadata = await ConsultationService.get_scholars_metadata(db)
    return success_response(data=metadata)


import math
from pydantic import BaseModel
from sqlalchemy import select
from app.db.models import Scholar, ScholarMeeting
from fastapi import HTTPException

class BookMeetingRequest(BaseModel):
    scholar_id: Optional[Any] = None
    scholarId: Optional[Any] = None
    user_name: Optional[str] = None
    userName: Optional[str] = None
    user_phone: Optional[str] = None
    userPhone: Optional[str] = None
    meeting_date: Optional[str] = None
    meetingDate: Optional[str] = None
    slot_time: Optional[str] = None
    timeSlot: Optional[str] = None
    topic: Optional[str] = None
    subject: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None

class UpdateScholarLocationRequest(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    mosque: Optional[str] = None
    meeting_slots: Optional[list] = None
    meetingSlots: Optional[list] = None

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

@router.get("/scholars/nearby", summary="جستجوی عالمان نزدیک بر اساس موقعیت مکانی و نقشه")
async def get_nearby_scholars(
    lat: float = Query(35.6892, description="عرض جغرافیایی کاربر"),
    lon: float = Query(51.3890, description="طول جغرافیایی کاربر"),
    radiusKm: Optional[float] = Query(None, description="شعاع جستجو بر حسب کیلومتر (اختیاری)"),
    madhhab: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scholar).where(Scholar.is_verified == True)
    if madhhab:
        stmt = stmt.where(Scholar.madhhab == madhhab)
    
    result = await db.scalars(stmt)
    scholars = result.all()

    items = []
    for s in scholars:
        s_lat = s.latitude or 35.6892
        s_lon = s.longitude or 51.3890
        dist = haversine_km(lat, lon, s_lat, s_lon)

        if radiusKm and dist > radiusKm:
            continue
        
        if specialty and specialty not in (s.specialties or []):
            continue

        items.append({
            "id": s.id,
            "name": s.name,
            "title": s.title,
            "specialties": s.specialties or [],
            "rating": s.rating or 5.0,
            "answerCount": s.answer_count or 0,
            "responseTimeHours": s.response_time_hours or 2,
            "rank": s.rank or 1,
            "avatarColorHex": s.avatar_color_hex or "0xFF8C6239",
            "avatarUrl": s.avatar_url,
            "madhhab": s.madhhab,
            "city": s.city,
            "mosque": s.mosque,
            "address": s.address or f"{s.city}، {s.mosque}",
            "latitude": s_lat,
            "longitude": s_lon,
            "distanceKm": dist,
            "meetingSlots": s.meeting_slots or [],
            "bio": s.bio
        })

    # Sort by distance
    items.sort(key=lambda x: x["distanceKm"])

    return success_response(data=items, meta={"total": len(items), "userCoordinates": {"lat": lat, "lon": lon}})

@router.post("/scholars/meetings/book", summary="رزرو وقت دیدار حضوری با عالم دینی")
async def book_scholar_meeting(
    data: BookMeetingRequest,
    db: AsyncSession = Depends(get_db)
):
    s_id = str(data.scholarId or data.scholar_id or "scholar_1")
    if not s_id.startswith("scholar_") and s_id.isdigit():
        s_id = f"scholar_{s_id}"

    scholar = await db.get(Scholar, s_id)
    if not scholar:
        # Fallback to first scholar
        scholar = (await db.scalars(select(Scholar).limit(1))).first()
    if not scholar:
        raise HTTPException(status_code=404, detail="عالم دینی مورد نظر یافت نشد.")

    u_name = data.userName or data.user_name or "کاربر گرامی"
    u_phone = data.userPhone or data.user_phone or "09120000000"
    m_date = data.meetingDate or data.meeting_date or "هفتگی طبق سانس"
    t_slot = data.timeSlot or data.slot_time or "جلسه و مشاوره حضوری"
    subj = data.subject or data.topic or "مشاوره و دیدار حضوری"
    loc = data.location or scholar.address or f"{scholar.city}، {scholar.mosque}"

    meeting_id = f"meet_{uuid.uuid4().hex[:8]}"
    meeting = ScholarMeeting(
        id=meeting_id,
        scholar_id=scholar.id,
        user_name=u_name,
        user_phone=u_phone,
        meeting_date=m_date,
        time_slot=t_slot,
        location=loc,
        subject=subj,
        notes=data.notes,
        status="PENDING"
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)

    tracking = f"ETT-{meeting.id[-6:].upper()}"
    return success_response(data={
        "meetingId": meeting.id,
        "scholarName": scholar.name,
        "meetingDate": meeting.meeting_date,
        "timeSlot": meeting.time_slot,
        "location": meeting.location,
        "status": meeting.status,
        "trackingCode": tracking,
        "tracking_code": tracking,
        "message": "درخواست وقت دیدار با موفقیت ثبت شد و به اطلاع دفتر استاد رسید."
    })

@router.get("/scholars/{scholar_id}/meetings", summary="دریافت وقت‌های دیدار و زمان‌های مشاوره یک عالم")
async def get_scholar_meetings(
    scholar_id: str,
    db: AsyncSession = Depends(get_db)
):
    s_id = scholar_id
    if not s_id.startswith("scholar_") and s_id.isdigit():
        s_id = f"scholar_{s_id}"

    scholar = await db.get(Scholar, s_id)
    if not scholar:
        scholar = (await db.scalars(select(Scholar).limit(1))).first()
    if not scholar:
        raise HTTPException(status_code=404, detail="استاد مورد نظر یافت نشد.")

    slots = scholar.meeting_slots or []

    stmt = select(ScholarMeeting).where(
        ScholarMeeting.scholar_id == scholar.id,
        ScholarMeeting.status.in_(["PENDING", "CONFIRMED"])
    ).order_by(ScholarMeeting.created_at.desc())
    booked = (await db.scalars(stmt)).all()

    return success_response(data={
        "scholarId": scholar.id,
        "scholarName": scholar.name,
        "address": scholar.address or f"{scholar.city}، {scholar.mosque}",
        "latitude": scholar.latitude,
        "longitude": scholar.longitude,
        "meetingSlots": slots,
        "bookedMeetings": [{
            "id": m.id,
            "meetingDate": m.meeting_date,
            "timeSlot": m.time_slot,
            "status": m.status
        } for m in booked]
    })

@router.put("/scholars/{scholar_id}/location", summary="ویرایش موقعیت جغرافیایی و وقت‌های دیدار توسط عالم")
async def update_scholar_location(
    scholar_id: str,
    data: UpdateScholarLocationRequest,
    db: AsyncSession = Depends(get_db)
):
    s_id = scholar_id
    if not s_id.startswith("scholar_") and s_id.isdigit():
        s_id = f"scholar_{s_id}"

    scholar = await db.get(Scholar, s_id)
    if not scholar:
        scholar = (await db.scalars(select(Scholar).limit(1))).first()
    if not scholar:
        raise HTTPException(status_code=404, detail="پروفایل عالم یافت نشد.")

    scholar.latitude = data.latitude
    scholar.longitude = data.longitude
    if data.address:
        scholar.address = data.address
    if data.city:
        scholar.city = data.city
    if data.mosque:
        scholar.mosque = data.mosque
    slots = data.meeting_slots if data.meeting_slots is not None else data.meetingSlots
    if slots is not None:
        scholar.meeting_slots = slots

    await db.commit()
    await db.refresh(scholar)

    return success_response(data={
        "scholarId": scholar.id,
        "latitude": scholar.latitude,
        "longitude": scholar.longitude,
        "address": scholar.address,
        "meetingSlots": scholar.meeting_slots,
        "message": "موقعیت مکانی و ساعات دیدار با موفقیت به‌روزرسانی شد."
    })


# 2.2 Consultation Threads
@router.post("/threads", status_code=201, summary="ثبت پرسش جدید در ویزارد مشاوره")
async def create_thread(
    data: CreateThreadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    created = await ConsultationService.create_thread(db, current_user.id, data)
    return success_response(data=created, status_code=201)


@router.get("/threads", summary="دریافت فهرست گفتگوهای کاربر")
async def get_threads(
    filter: str = Query("ALL", description="ALL, PENDING, ANSWERED, BOOKMARKED, PUBLIC"),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort: str = Query("LAST_ACTIVITY", description="LAST_ACTIVITY, NEWEST"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await ConsultationService.get_threads(
        db=db,
        user_id=current_user.id,
        role=current_user.role,
        filter_type=filter,
        category=category,
        q=q,
        sort=sort,
        page=page,
        limit=limit
    )
    return success_response(
        data=[t.model_dump() for t in result["items"]],
        meta=result["meta"]
    )


@router.get("/threads/public", summary="دریافت استفتائات و پرسش‌های عمومی پاسخ‌داده‌شده (بدون نیاز به لاگین)")
async def get_public_threads(
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    sort: str = Query("LAST_ACTIVITY", description="LAST_ACTIVITY, NEWEST"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    result = await ConsultationService.get_threads(
        db=db,
        user_id="",
        role="SEEKER",
        filter_type="PUBLIC",
        category=category,
        q=q,
        sort=sort,
        page=page,
        limit=limit
    )
    return success_response(
        data=[t.model_dump() for t in result["items"]],
        meta=result["meta"]
    )



@router.get("/threads/{threadId}", summary="دریافت جزئیات و تاریخچه پیام‌های گفتگو")
async def get_thread_detail(
    threadId: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    detail = await ConsultationService.get_thread_detail(
        db=db,
        thread_id=threadId,
        user_id=current_user.id,
        role=current_user.role
    )
    return success_response(data=detail.model_dump())


@router.post("/threads/{threadId}/messages", summary="ارسال پیام جدید در رشته‌گفتگو")
async def create_message(
    threadId: str,
    data: CreateMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    msg = await ConsultationService.send_message(
        db=db,
        thread_id=threadId,
        user_id=current_user.id,
        role=current_user.role,
        data=data
    )
    return success_response(data=msg.model_dump())


@router.patch("/threads/{threadId}/status", summary="تغییر وضعیت گفتگو به OPEN یا CLOSED")
async def update_thread_status(
    threadId: str,
    data: UpdateThreadStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await ConsultationService.update_thread_status(db, threadId, current_user.id, data.status)
    return success_response(data=res)


@router.post("/threads/{threadId}/bookmark", summary="نشان‌کردن / لغو نشان گفتگو")
async def toggle_thread_bookmark(
    threadId: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await ConsultationService.toggle_bookmark(db, threadId, current_user.id)
    return success_response(data=res)


@router.patch("/threads/{threadId}/visibility", summary="تغییر وضعیت نمایش عمومی یا خصوصی گفتگو")
async def update_thread_visibility(
    threadId: str,
    data: UpdateThreadVisibilityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await ConsultationService.update_visibility(db, threadId, current_user.id, data.isPublic)
    return success_response(data=res)


# 2.3 Scholar Portal & Quick Replies
@router.get("/scholar/inbox", summary="کارتابل اختصاصی سوالات ارجاعی به عالم")
async def get_scholar_inbox(
    current_user: User = Depends(require_scholar),
    db: AsyncSession = Depends(get_db)
):
    items = await ConsultationService.get_scholar_inbox(db, current_user.id)
    return success_response(data=[i.model_dump() for i in items])


@router.get("/scholar/quick-replies", summary="لیست پاسخ‌های آماده عالم")
async def get_quick_replies(
    current_user: User = Depends(require_scholar),
    db: AsyncSession = Depends(get_db)
):
    replies = await ConsultationService.get_quick_replies(db, current_user.id)
    return success_response(data=[
        {
            "id": r.id,
            "title": r.title,
            "content": r.content,
            "category": r.category
        } for r in replies
    ])


@router.post("/scholar/quick-replies", summary="افزودن پاسخ آماده شخصی جدید توسط عالم")
async def create_quick_reply(
    data: CreateQuickReplyRequest,
    current_user: User = Depends(require_scholar),
    db: AsyncSession = Depends(get_db)
):
    reply = await ConsultationService.create_quick_reply(db, current_user.id, data)
    return success_response(data={
        "id": reply.id,
        "title": reply.title,
        "content": reply.content,
        "category": reply.category
    })


@router.post("/media/upload", summary="آپلود صوت، تصویر یا ویدئوی ضمیمه")
async def upload_media(
    file: UploadFile = File(...),
    type: str = Form("VOICE"),
    title: Optional[str] = Form("فایل ضمیمه"),
    durationSeconds: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user)
):
    # Verify file size
    file_bytes = await file.read()
    file_size = len(file_bytes)

    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise AttachmentOversizeException(
            message=f"حجم فایل ارسالی بیش از سقف مجاز (۲۵ مگابایت) است.",
            details={
                "field": "file",
                "limitBytes": settings.MAX_UPLOAD_SIZE_BYTES,
                "receivedBytes": file_size
            }
        )

    # Save to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ".bin"
    media_id = f"att_{type.lower()}_{uuid.uuid4().hex[:8]}"
    filename = f"{media_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    file_url = f"{settings.STATIC_URL_PREFIX}/uploads/{filename}"

    return success_response(data={
        "mediaId": media_id,
        "type": type,
        "title": title or file.filename,
        "durationSeconds": durationSeconds,
        "fileUrl": file_url,
        "fileSizeBytes": file_size
    })


@router.post("/threads/{threadId}/ai-draft", summary="پیشنهاد پیش‌نویس پاسخ هوشمند برای سوال مشاوره توسط هوش مصنوعی")
async def generate_consultation_ai_draft(
    threadId: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    draft = await ConsultationService.generate_ai_draft_response(db, threadId, current_user.id)
    return success_response(data=draft)


@router.get("/scholar/books/search", summary="جستجوی کتاب‌ها و فصول کتابخانه جهت ارجاع و استناد توسط عالم و کاربر")
async def search_books_for_scholar(
    q: Optional[str] = Query(None, description="عبارت جستجو در عنوان، نویسنده یا موضوعات"),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    results = await ConsultationService.search_books_for_citation(db, query=q, limit=limit)
    return success_response(data=results)


@router.post("/threads/{threadId}/suggest-citations", summary="پیشنهاد هوشمند ۲ الی ۳ ارجاع و بند کتاب مرتبط با سوال گفتگو برای عالم")
async def suggest_thread_citations(
    threadId: str,
    current_user: User = Depends(require_scholar),
    db: AsyncSession = Depends(get_db)
):
    suggestions = await ConsultationService.suggest_citations_for_thread(db, threadId, current_user.id)
    return success_response(data=[s.model_dump() for s in suggestions])


class CreateScholarPostRequest(BaseModel):
    title: str
    content: str
    post_type: Optional[str] = "ARTICLE"
    audio_url: Optional[str] = None
    audio_duration_seconds: Optional[int] = None
    tags: Optional[List[str]] = None
    book_reference: Optional[Dict[str, Any]] = None


class UpdateScholarProfileSelfRequest(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    bio: Optional[str] = None
    specialties: Optional[List[str]] = None
    mosque: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    meeting_slots: Optional[List[Any]] = None


@router.post("/scholars/posts", summary="انتشار یادداشت، درس‌گفتار صوتی یا فتوا توسط عالم دینی")
async def create_scholar_post(
    data: CreateScholarPostRequest,
    current_user: User = Depends(require_scholar),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scholar).where(Scholar.user_id == current_user.id)
    scholar = await db.scalar(stmt)
    if not scholar:
        # Fallback to any scholar record or create virtual
        scholar_id = f"sch_{current_user.id}"
        scholar = Scholar(
            id=scholar_id,
            user_id=current_user.id,
            name=current_user.full_name,
            title="استاد حوزه علمیه و معارف اسلامی",
            madhhab=current_user.madhhab,
            city="قم",
            mosque=current_user.mosque_name or "مسجد جامع",
            bio="پژوهشگر معارف اسلامی و پاسخ‌گوی استفتائات",
            is_verified=True
        )
        db.add(scholar)
        await db.commit()
        await db.refresh(scholar)

    from app.db.models.scholar import ScholarPost
    post_id = f"post_{uuid.uuid4().hex[:12]}"
    post = ScholarPost(
        id=post_id,
        scholar_id=scholar.id,
        title=data.title,
        content=data.content,
        post_type=data.post_type or "ARTICLE",
        audio_url=data.audio_url,
        audio_duration_seconds=data.audio_duration_seconds,
        tags=data.tags or [],
        book_reference=data.book_reference
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    return success_response(data={
        "id": post.id,
        "scholarId": post.scholar_id,
        "title": post.title,
        "content": post.content,
        "postType": post.post_type,
        "audioUrl": post.audio_url,
        "audioDurationSeconds": post.audio_duration_seconds,
        "tags": post.tags,
        "bookReference": post.book_reference,
        "createdAt": post.created_at.isoformat() if post.created_at else None
    })


@router.get("/scholars/{scholarId}/posts", summary="دریافت فهرست مطالب، درس‌گفتارها و آثار منتشرشده عالم")
async def get_scholar_posts(
    scholarId: str,
    db: AsyncSession = Depends(get_db)
):
    from app.db.models.scholar import ScholarPost
    stmt = select(ScholarPost).where(ScholarPost.scholar_id == scholarId).order_by(ScholarPost.created_at.desc())
    result = await db.scalars(stmt)
    posts = result.all()

    items = []
    for p in posts:
        items.append({
            "id": p.id,
            "scholarId": p.scholar_id,
            "title": p.title,
            "content": p.content,
            "postType": p.post_type,
            "audioUrl": p.audio_url,
            "audioDurationSeconds": p.audio_duration_seconds,
            "tags": p.tags or [],
            "bookReference": p.book_reference,
            "likesCount": p.likes_count,
            "createdAt": p.created_at.isoformat() if p.created_at else None
        })
    return success_response(data=items)


@router.put("/scholars/my-profile", summary="کنترل و ویرایش صفحه شخصی، مشخصات و نوبت‌های مسجد توسط عالم دینی")
async def update_my_scholar_profile(
    data: UpdateScholarProfileSelfRequest,
    current_user: User = Depends(require_scholar),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Scholar).where(Scholar.user_id == current_user.id)
    scholar = await db.scalar(stmt)
    if not scholar:
        scholar = Scholar(
            id=f"sch_{current_user.id}",
            user_id=current_user.id,
            name=data.name or current_user.full_name,
            title=data.title or "عالم دینی و استاد معارف",
            madhhab=current_user.madhhab,
            city=data.city or "تهران",
            mosque=data.mosque or current_user.mosque_name or "مسجد جامع",
            address=data.address or current_user.mosque_address or "",
            bio=data.bio or "مدرس سطوح عالی و پاسخگوی استفتائات معاصر",
            is_verified=True,
            meeting_slots=data.meeting_slots or []
        )
        db.add(scholar)
    else:
        if data.name: scholar.name = data.name
        if data.title: scholar.title = data.title
        if data.bio: scholar.bio = data.bio
        if data.specialties is not None: scholar.specialties = data.specialties
        if data.mosque: scholar.mosque = data.mosque
        if data.city: scholar.city = data.city
        if data.address: scholar.address = data.address
        if data.meeting_slots is not None: scholar.meeting_slots = data.meeting_slots

    if data.mosque:
        current_user.mosque_name = data.mosque
    if data.address:
        current_user.mosque_address = data.address

    await db.commit()
    await db.refresh(scholar)

    return success_response(data={
        "id": scholar.id,
        "name": scholar.name,
        "title": scholar.title,
        "bio": scholar.bio,
        "specialties": scholar.specialties,
        "mosque": scholar.mosque,
        "city": scholar.city,
        "address": scholar.address,
        "meetingSlots": scholar.meeting_slots,
        "isVerified": scholar.is_verified
    })
