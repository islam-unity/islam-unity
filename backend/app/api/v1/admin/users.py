from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.response import success_response
from app.db.models import User, PersonaConfig
from app.db.session import get_db
from app.api.v1.admin.common import UserStatusUpdate, paginate

router = APIRouter()


def serialize_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "phoneNumber": user.phone_number,
        "phone_number": user.phone_number,
        "fullName": user.full_name,
        "full_name": user.full_name,
        "role": user.role,
        "madhhab": user.madhhab,
        "isActive": user.is_active,
        "is_active": user.is_active,
        "age": user.age,
        "gender": user.gender,
        "education": user.education,
        "interests": user.interests or [],
        "knowledgeLevel": user.knowledge_level,
        "knowledge_level": user.knowledge_level,
        "learningGoals": user.learning_goals,
        "learning_goals": user.learning_goals,
        "avatar": user.avatar,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


def serialize_persona(persona: Optional[PersonaConfig]) -> Optional[Dict[str, Any]]:
    if not persona:
        return None
    return {
        "id": persona.id,
        "userId": persona.user_id,
        "user_id": persona.user_id,
        "botName": persona.bot_name,
        "bot_name": persona.bot_name,
        "botRolePreset": persona.bot_role_preset,
        "bot_role_preset": persona.bot_role_preset,
        "botAvatar": persona.bot_avatar,
        "bot_avatar": persona.bot_avatar,
        "tone": persona.tone,
        "fiqhApproach": persona.fiqh_approach,
        "fiqh_approach": persona.fiqh_approach,
        "detailLevel": persona.detail_level,
        "detail_level": persona.detail_level,
        "includeAyahAddress": persona.include_ayah_address,
        "include_ayah_address": persona.include_ayah_address,
        "includeHadithReferences": persona.include_hadith_references,
        "include_hadith_references": persona.include_hadith_references,
        "customPromptInstructions": persona.custom_prompt_instructions,
        "custom_prompt_instructions": persona.custom_prompt_instructions
    }


@router.get("", summary="فهرست صفحه‌بندی‌شده کاربران با فیلتر و جستجو")
async def list_users(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: str = Query("desc"),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(User)

    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(search_pattern),
                User.phone_number.ilike(search_pattern)
            )
        )

    if role:
        stmt = stmt.where(User.role == role)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)

    # Sorting
    sort_column = User.created_at
    if sortBy:
        lower_sort = sortBy.lower()
        if lower_sort in ["fullname", "full_name"]:
            sort_column = User.full_name
        elif lower_sort in ["phonenumber", "phone_number"]:
            sort_column = User.phone_number
        elif lower_sort == "role":
            sort_column = User.role
        elif lower_sort == "id":
            sort_column = User.id

    if sortOrder.lower() == "asc":
        stmt = stmt.order_by(sort_column.asc())
    else:
        stmt = stmt.order_by(sort_column.desc())

    users, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_user(u) for u in users],
        meta=meta
    )


@router.get("/{id}", summary="دریافت شناسنامه کاربر همراه با تنظیمات پرسونا")
async def get_user_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(User).options(selectinload(User.persona)).where(User.id == id)
    user = await db.scalar(stmt)
    if not user:
        raise HTTPException(status_code=404, detail="کاربر مورد نظر یافت نشد.")

    data = serialize_user(user)
    data["persona"] = serialize_persona(user.persona)
    return success_response(data=data)


@router.patch("/{id}/status", summary="تغییر وضعیت فعال یا معلق بودن کاربر (عملیات سریع)")
async def update_user_status(
    id: str,
    body: UserStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    user = await db.scalar(select(User).where(User.id == id))
    if not user:
        raise HTTPException(status_code=404, detail="کاربر مورد نظر یافت نشد.")

    user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)

    return success_response(data=serialize_user(user))
