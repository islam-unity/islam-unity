from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.models import (
    User, Scholar, ConsultationThread, AIUsageLog, PostReport
)
from app.db.session import get_db

router = APIRouter()


@router.get("/overview", summary="دریافت شاخص‌های کلیدی و آمار داشبورد ادمین")
async def get_overview(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    # 1. Total users
    total_users = (await db.scalar(select(func.count(User.id)))) or 0

    # 2. Total scholars
    total_scholars = (await db.scalar(select(func.count(Scholar.id)))) or 0

    # 3. Open consultation threads
    open_threads = (await db.scalar(
        select(func.count(ConsultationThread.id)).where(
            ConsultationThread.status.in_(["WAITING_SCHOLAR", "OPEN"])
        )
    )) or 0

    # 4. Total AI tokens consumed
    ai_tokens_consumed = (await db.scalar(
        select(func.coalesce(func.sum(AIUsageLog.total_tokens), 0))
    )) or 0

    # 5. Content reports count (pending reports)
    pending_reports = (await db.scalar(
        select(func.count(PostReport.id)).where(PostReport.status == "PENDING")
    )) or 0
    total_reports = (await db.scalar(select(func.count(PostReport.id)))) or 0

    # 6. System health
    system_health = {
        "status": "healthy",
        "database": "connected"
    }

    data = {
        "totalUsers": total_users,
        "total_users": total_users,
        "usersCount": total_users,
        "totalScholars": total_scholars,
        "total_scholars": total_scholars,
        "scholarsCount": total_scholars,
        "openThreads": open_threads,
        "open_threads": open_threads,
        "openThreadsCount": open_threads,
        "aiTokensConsumed": ai_tokens_consumed,
        "ai_tokens_consumed": ai_tokens_consumed,
        "totalTokens": ai_tokens_consumed,
        "contentReportsCount": pending_reports if pending_reports > 0 else total_reports,
        "content_reports_count": pending_reports if pending_reports > 0 else total_reports,
        "pendingReportsCount": pending_reports,
        "totalReportsCount": total_reports,
        "systemHealth": system_health,
        "system_health": system_health
    }

    return success_response(data=data)
