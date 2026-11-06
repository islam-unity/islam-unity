import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.response import success_response
from app.db.models import (
    User, Scholar, ConsultationThread, ConsultationMessage, ConsultationAttachment
)
from app.db.session import get_db
from app.api.v1.admin.common import (
    ThreadStatusUpdate, ThreadReplyRequest, paginate
)

router = APIRouter()


class CreateScholarRequest(BaseModel):
    id: Optional[str] = None
    userId: Optional[str] = None
    user_id: Optional[str] = None
    name: str
    title: str
    specialties: Optional[List[str]] = None
    rating: Optional[float] = 5.0
    answerCount: Optional[int] = 0
    answer_count: Optional[int] = None
    responseTimeHours: Optional[int] = 4
    response_time_hours: Optional[int] = None
    rank: Optional[int] = 1
    avatarColorHex: Optional[str] = "0xFF0F5257"
    avatar_color_hex: Optional[str] = None
    avatarUrl: Optional[str] = None
    avatar_url: Optional[str] = None
    isVerified: Optional[bool] = True
    is_verified: Optional[bool] = None
    madhhab: str
    city: str
    mosque: str
    bio: str


def serialize_scholar(scholar: Scholar) -> Dict[str, Any]:
    return {
        "id": scholar.id,
        "userId": scholar.user_id,
        "user_id": scholar.user_id,
        "name": scholar.name,
        "title": scholar.title,
        "specialties": scholar.specialties or [],
        "rating": scholar.rating,
        "answerCount": scholar.answer_count,
        "answer_count": scholar.answer_count,
        "responseTimeHours": scholar.response_time_hours,
        "response_time_hours": scholar.response_time_hours,
        "rank": scholar.rank,
        "avatarColorHex": scholar.avatar_color_hex,
        "avatarUrl": scholar.avatar_url,
        "avatar_url": scholar.avatar_url,
        "isVerified": scholar.is_verified,
        "is_verified": scholar.is_verified,
        "madhhab": scholar.madhhab,
        "city": scholar.city,
        "mosque": scholar.mosque,
        "bio": scholar.bio
    }


def serialize_attachment(att: ConsultationAttachment) -> Dict[str, Any]:
    return {
        "id": att.id,
        "threadId": att.thread_id,
        "thread_id": att.thread_id,
        "uploaderId": att.uploader_id,
        "uploader_id": att.uploader_id,
        "type": att.type,
        "title": att.title,
        "durationSeconds": att.duration_seconds,
        "duration_seconds": att.duration_seconds,
        "fileUrl": att.file_url,
        "file_url": att.file_url,
        "fileSizeBytes": att.file_size_bytes,
        "file_size_bytes": att.file_size_bytes,
        "createdAt": att.created_at.isoformat() if att.created_at else None,
        "created_at": att.created_at.isoformat() if att.created_at else None
    }


def serialize_message(msg: ConsultationMessage) -> Dict[str, Any]:
    return {
        "id": msg.id,
        "threadId": msg.thread_id,
        "thread_id": msg.thread_id,
        "senderId": msg.sender_id,
        "sender_id": msg.sender_id,
        "senderRole": msg.sender_role,
        "sender_role": msg.sender_role,
        "text": msg.text,
        "citation": msg.citation,
        "attachmentId": msg.attachment_id,
        "attachment_id": msg.attachment_id,
        "isRead": msg.is_read,
        "is_read": msg.is_read,
        "createdAt": msg.created_at.isoformat() if msg.created_at else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else None
    }


def serialize_thread(thread: ConsultationThread) -> Dict[str, Any]:
    return {
        "id": thread.id,
        "userId": thread.user_id,
        "user_id": thread.user_id,
        "targetScholarId": thread.target_scholar_id,
        "target_scholar_id": thread.target_scholar_id,
        "title": thread.title,
        "category": thread.category,
        "trackingCode": thread.tracking_code,
        "tracking_code": thread.tracking_code,
        "status": thread.status,
        "isAnonymous": thread.is_anonymous,
        "is_anonymous": thread.is_anonymous,
        "isPublic": thread.is_public,
        "is_public": thread.is_public,
        "isUrgent": thread.is_urgent,
        "is_urgent": thread.is_urgent,
        "isBookmarked": thread.is_bookmarked,
        "is_bookmarked": thread.is_bookmarked,
        "createdAt": thread.created_at.isoformat() if thread.created_at else None,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "updatedAt": thread.updated_at.isoformat() if thread.updated_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None
    }


@router.get("/scholars", summary="فهرست اساتید و مبلغان")
async def list_scholars(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(Scholar)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Scholar.name.ilike(search_pattern),
                Scholar.city.ilike(search_pattern),
                Scholar.madhhab.ilike(search_pattern)
            )
        )
    stmt = stmt.order_by(Scholar.rank.asc(), Scholar.answer_count.desc())

    scholars, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_scholar(s) for s in scholars],
        meta=meta
    )


@router.post("/scholars", summary="افزودن و ثبت عالم دینی / استاد جدید")
async def create_scholar(
    payload: CreateScholarRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    sch_id = payload.id or f"sch_{uuid.uuid4().hex[:8]}"
    existing = await db.scalar(select(Scholar).where(Scholar.id == sch_id))
    if existing:
        raise HTTPException(status_code=400, detail="استادی با این شناسه قبلاً ثبت شده است.")

    u_id = payload.userId or payload.user_id
    ans_cnt = payload.answerCount if payload.answerCount is not None else (payload.answer_count or 0)
    resp_hours = payload.responseTimeHours if payload.responseTimeHours is not None else (payload.response_time_hours or 4)
    color = payload.avatarColorHex or payload.avatar_color_hex or "0xFF0F5257"
    avatar = payload.avatarUrl or payload.avatar_url
    verified = payload.isVerified if payload.isVerified is not None else (payload.is_verified if payload.is_verified is not None else True)

    scholar = Scholar(
        id=sch_id,
        user_id=u_id,
        name=payload.name.strip(),
        title=payload.title.strip(),
        specialties=payload.specialties or [],
        rating=payload.rating or 5.0,
        answer_count=ans_cnt,
        response_time_hours=resp_hours,
        rank=payload.rank or 1,
        avatar_color_hex=color,
        avatar_url=avatar,
        is_verified=verified,
        madhhab=payload.madhhab.strip(),
        city=payload.city.strip(),
        mosque=payload.mosque.strip(),
        bio=payload.bio.strip()
    )
    db.add(scholar)
    await db.commit()
    await db.refresh(scholar)
    return success_response(
        data=serialize_scholar(scholar),
        meta={"message": f"عالم دینی '{scholar.name}' با موفقیت در سامانه ثبت شد."}
    )


@router.delete("/scholars/{scholar_id}", summary="حذف عالم دینی")
async def delete_scholar(
    scholar_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    scholar = await db.scalar(select(Scholar).where(Scholar.id == scholar_id))
    if not scholar:
        raise HTTPException(status_code=404, detail="عالم دینی مورد نظر یافت نشد.")
    await db.delete(scholar)
    await db.commit()
    return success_response(data={"deleted": True, "id": scholar_id})


@router.get("/threads", summary="فهرست صفحه‌بندی‌شده تریدهای مشاوره با فیلترها")
async def list_threads(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    is_urgent: Optional[bool] = Query(None),
    isUrgent: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    tracking_code: Optional[str] = Query(None),
    trackingCode: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(ConsultationThread)

    # Urgent filter
    urgent_val = is_urgent if is_urgent is not None else isUrgent
    if urgent_val is not None:
        stmt = stmt.where(ConsultationThread.is_urgent == urgent_val)

    # Status filter
    if status:
        stmt = stmt.where(ConsultationThread.status == status)

    # Tracking code filter
    tc = tracking_code or trackingCode
    if tc:
        stmt = stmt.where(ConsultationThread.tracking_code.ilike(f"%{tc}%"))

    # Search filter
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                ConsultationThread.title.ilike(search_pattern),
                ConsultationThread.tracking_code.ilike(search_pattern),
                ConsultationThread.category.ilike(search_pattern)
            )
        )

    # Sorting
    sort_col = ConsultationThread.created_at
    if sortBy:
        lower = sortBy.lower()
        if lower in ["title"]:
            sort_col = ConsultationThread.title
        elif lower in ["status"]:
            sort_col = ConsultationThread.status
        elif lower in ["isurgent", "is_urgent"]:
            sort_col = ConsultationThread.is_urgent

    if sortOrder.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    threads, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_thread(t) for t in threads],
        meta=meta
    )


@router.get("/threads/{id}", summary="دریافت جزئیات ترید مشاوره به همراه پیام‌ها و پیوست‌ها")
async def get_thread_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = (
        select(ConsultationThread)
        .options(
            selectinload(ConsultationThread.messages),
            selectinload(ConsultationThread.attachments)
        )
        .where(ConsultationThread.id == id)
    )
    thread = await db.scalar(stmt)
    if not thread:
        raise HTTPException(status_code=404, detail="ترید مشاوره مورد نظر یافت نشد.")

    data = serialize_thread(thread)
    data["messages"] = [serialize_message(m) for m in (thread.messages or [])]
    data["attachments"] = [serialize_attachment(a) for a in (thread.attachments or [])]

    return success_response(data=data)


@router.patch("/threads/{id}/status", summary="تغییر سریع وضعیت ترید مشاوره")
async def update_thread_status(
    id: str,
    body: ThreadStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == id))
    if not thread:
        raise HTTPException(status_code=404, detail="ترید مشاوره مورد نظر یافت نشد.")

    thread.status = body.status
    await db.commit()
    await db.refresh(thread)

    return success_response(data=serialize_thread(thread))


@router.post("/threads/{id}/reply", summary="ارسال پاسخ سریع در ترید مشاوره")
async def reply_to_thread(
    id: str,
    body: ThreadReplyRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == id))
    if not thread:
        raise HTTPException(status_code=404, detail="ترید مشاوره مورد نظر یافت نشد.")

    sender_id = body.sender_id or thread.target_scholar_id or "usr_admin_1"
    msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    new_message = ConsultationMessage(
        id=msg_id,
        thread_id=thread.id,
        sender_id=sender_id,
        sender_role=body.sender_role or "SCHOLAR",
        text=body.text,
        citation=body.citation,
        is_read=False
    )
    db.add(new_message)

    thread.status = "ANSWERED"
    await db.commit()
    await db.refresh(new_message)

    return success_response(data=serialize_message(new_message))


@router.get("/pending-scholars", summary="فهرست درخواست‌های عضویت علما در انتظار بررسی ادمین")
async def list_pending_scholars(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(User).where(User.scholar_status == "PENDING").order_by(User.created_at.desc())
    users = (await db.scalars(stmt)).all()
    
    items = []
    for u in users:
        items.append({
            "id": u.id,
            "fullName": u.full_name,
            "phoneNumber": u.phone_number,
            "role": u.role,
            "scholarStatus": u.scholar_status,
            "mosqueName": u.mosque_name or "ثبت نشده",
            "mosqueAddress": u.mosque_address or "ثبت نشده",
            "madhhab": u.madhhab,
            "createdAt": u.created_at.isoformat() if u.created_at else None
        })
    return success_response(data=items, meta={"total": len(items)})


@router.post("/scholars/{user_id}/approve", summary="تایید و فعال‌سازی درخواست عضویت عالم دینی")
async def approve_scholar(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="کاربر مورد نظر یافت نشد.")

    user.role = "SCHOLAR"
    user.scholar_status = "APPROVED"

    # Check or create scholar profile
    scholar = await db.scalar(select(Scholar).where(Scholar.user_id == user.id))
    if not scholar:
        scholar_id = f"sch_{user.id}"
        scholar = Scholar(
            id=scholar_id,
            user_id=user.id,
            name=user.full_name,
            title="عالم دینی و استاد معارف اسلامی",
            specialties=["فقه و احکام شرعی", "تفسیر قرآن", "پاسخ به سوالات دینی"],
            rating=5.0,
            answer_count=0,
            response_time_hours=4,
            rank=1,
            avatar_color_hex="0xFF8C6239",
            is_verified=True,
            madhhab=user.madhhab or "شیعه اثناعشری",
            city="تهران",
            mosque=user.mosque_name or "مسجد جامع",
            address=user.mosque_address or "",
            bio=f"عالم دینی و امام جماعت {user.mosque_name or 'مسجد'}; پاسخگوی احکام و استفتائات شرعی برادران و خواهران ایمانی."
        )
        db.add(scholar)
    else:
        scholar.is_verified = True
        if user.mosque_name:
            scholar.mosque = user.mosque_name
        if user.mosque_address:
            scholar.address = user.mosque_address

    await db.commit()
    await db.refresh(user)

    return success_response(data={
        "userId": user.id,
        "fullName": user.full_name,
        "role": user.role,
        "scholarStatus": user.scholar_status,
        "message": "عالم دینی با موفقیت تایید و دسترسی‌های ویژه وی فعال گردید."
    })


@router.post("/scholars/{user_id}/reject", summary="رد درخواست عضویت عالم دینی")
async def reject_scholar(
    user_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    user = await db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="کاربر مورد نظر یافت نشد.")

    user.scholar_status = "REJECTED"
    user.role = "SEEKER"
    await db.commit()
    await db.refresh(user)

    return success_response(data={
        "userId": user.id,
        "fullName": user.full_name,
        "role": user.role,
        "scholarStatus": user.scholar_status,
        "message": "درخواست عضویت عالم رد شد و کاربر به عنوان کاربر عادی باقی ماند."
    })
