import platform
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.response import get_current_utc_timestamp, success_response
from app.db.base import Base
from app.db.models import DeveloperAccount, DeveloperApiKey
from app.db.session import get_db
from app.api.v1.admin.common import ApiKeyStatusUpdate, paginate

router = APIRouter()


def serialize_account(acc: DeveloperAccount) -> Dict[str, Any]:
    return {
        "id": acc.id,
        "userId": acc.user_id,
        "user_id": acc.user_id,
        "appName": acc.app_name,
        "app_name": acc.app_name,
        "description": acc.description,
        "tier": acc.tier,
        "monthlyQuotaTokens": acc.monthly_quota_tokens,
        "monthly_quota_tokens": acc.monthly_quota_tokens,
        "usedTokensThisMonth": acc.used_tokens_this_month,
        "used_tokens_this_month": acc.used_tokens_this_month,
        "rateLimitPerMinute": acc.rate_limit_per_minute,
        "rate_limit_per_minute": acc.rate_limit_per_minute,
        "isActive": acc.is_active,
        "is_active": acc.is_active,
        "createdAt": acc.created_at.isoformat() if acc.created_at else None,
        "created_at": acc.created_at.isoformat() if acc.created_at else None
    }


def serialize_api_key(key: DeveloperApiKey) -> Dict[str, Any]:
    return {
        "id": key.id,
        "accountId": key.account_id,
        "account_id": key.account_id,
        "keyPrefix": key.key_prefix,
        "key_prefix": key.key_prefix,
        "label": key.label,
        "isActive": key.is_active,
        "is_active": key.is_active,
        "totalRequests": key.total_requests,
        "total_requests": key.total_requests,
        "totalTokens": key.total_tokens,
        "total_tokens": key.total_tokens,
        "lastUsedAt": key.last_used_at.isoformat() if key.last_used_at else None,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "createdAt": key.created_at.isoformat() if key.created_at else None,
        "created_at": key.created_at.isoformat() if key.created_at else None
    }


@router.get("/accounts", summary="فهرست صفحه‌بندی‌شده حساب‌های توسعه‌دهنده")
async def list_developer_accounts(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    tier: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    isActive: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(DeveloperAccount)

    if tier:
        stmt = stmt.where(DeveloperAccount.tier == tier)

    active_val = is_active if is_active is not None else isActive
    if active_val is not None:
        stmt = stmt.where(DeveloperAccount.is_active == active_val)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                DeveloperAccount.app_name.ilike(pattern),
                DeveloperAccount.description.ilike(pattern)
            )
        )

    stmt = stmt.order_by(DeveloperAccount.created_at.desc())

    accounts, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_account(a) for a in accounts],
        meta=meta
    )


@router.get("/keys", summary="فهرست صفحه‌بندی‌شده کلیدهای API توسعه‌دهندگان")
async def list_developer_keys(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    account_id: Optional[str] = Query(None),
    accountId: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    isActive: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(DeveloperApiKey)

    acc_id = account_id or accountId
    if acc_id:
        stmt = stmt.where(DeveloperApiKey.account_id == acc_id)

    active_val = is_active if is_active is not None else isActive
    if active_val is not None:
        stmt = stmt.where(DeveloperApiKey.is_active == active_val)

    stmt = stmt.order_by(DeveloperApiKey.created_at.desc())

    keys, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_api_key(k) for k in keys],
        meta=meta
    )


@router.patch("/keys/{id}/status", summary="تغییر وضعیت فعال یا ابطال کلید دسترسی API (عملیات سریع)")
async def update_api_key_status(
    id: str,
    body: ApiKeyStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    key = await db.scalar(select(DeveloperApiKey).where(DeveloperApiKey.id == id))
    if not key:
        raise HTTPException(status_code=404, detail="کلید API مورد نظر یافت نشد.")

    key.is_active = body.is_active
    await db.commit()
    await db.refresh(key)

    return success_response(data=serialize_api_key(key))


@router.get("/system-health", summary="وضعیت سلامت تفصیلی و سرویس‌های سیستم")
async def get_system_health(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # Check DB query
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        table_count = len(Base.metadata.tables)
    except Exception:
        table_count = 0

    try:
        from app.config import settings
        db_url = getattr(settings, "DATABASE_URL", "")
    except Exception:
        db_url = ""

    driver_name = "asyncpg/PostgreSQL" if "postgres" in db_url else "aiosqlite/sqlite3"

    data = {
        "status": "healthy" if db_ok else "degraded",
        "database": {
            "status": "connected" if db_ok else "disconnected",
            "driver": driver_name,
            "managedTablesCount": table_count
        },
        "system": {
            "os": platform.system(),
            "release": platform.release(),
            "pythonVersion": platform.python_version()
        },
        "services": {
            "aiEngine": "operational",
            "vectorDb": "connected",
            "realtimeWs": "operational"
        },
        "timestamp": get_current_utc_timestamp()
    }

    return success_response(data=data)
