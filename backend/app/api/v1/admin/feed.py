from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.response import success_response
from app.db.models import Post, PostReport
from app.db.session import get_db
from app.api.v1.admin.common import ReportStatusUpdate, paginate

router = APIRouter()


def serialize_post(post: Post) -> Dict[str, Any]:
    return {
        "id": post.id,
        "userId": post.user_id,
        "user_id": post.user_id,
        "scholarId": post.scholar_id,
        "scholar_id": post.scholar_id,
        "isScholarPost": post.is_scholar_post,
        "is_scholar_post": post.is_scholar_post,
        "title": post.title,
        "content": post.content,
        "contentType": post.content_type,
        "content_type": post.content_type,
        "category": post.category,
        "madhhab": post.madhhab,
        "quranReferences": post.quran_references or [],
        "quran_references": post.quran_references or [],
        "hadithReferences": post.hadith_references or [],
        "hadith_references": post.hadith_references or [],
        "tags": post.tags or [],
        "status": post.status,
        "moderationNote": post.moderation_note,
        "moderation_note": post.moderation_note,
        "viewsCount": post.views_count,
        "views_count": post.views_count,
        "likesCount": post.likes_count,
        "likes_count": post.likes_count,
        "commentsCount": post.comments_count,
        "comments_count": post.comments_count,
        "sharesCount": post.shares_count,
        "shares_count": post.shares_count,
        "savesCount": post.saves_count,
        "saves_count": post.saves_count,
        "aiSummary": post.ai_summary,
        "ai_summary": post.ai_summary,
        "createdAt": post.created_at.isoformat() if post.created_at else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updatedAt": post.updated_at.isoformat() if post.updated_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None
    }


def serialize_report(report: PostReport) -> Dict[str, Any]:
    return {
        "id": report.id,
        "postId": report.post_id,
        "post_id": report.post_id,
        "userId": report.user_id,
        "user_id": report.user_id,
        "reason": report.reason,
        "description": report.description,
        "status": report.status,
        "createdAt": report.created_at.isoformat() if report.created_at else None,
        "created_at": report.created_at.isoformat() if report.created_at else None
    }


@router.get("/posts", summary="فهرست صفحه‌بندی‌شده پست‌های فید با فیلترها")
async def list_posts(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    scholar_id: Optional[str] = Query(None),
    scholarId: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    sortBy: Optional[str] = Query(None),
    sortOrder: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(Post)

    if status:
        stmt = stmt.where(Post.status == status)

    s_id = scholar_id or scholarId
    if s_id:
        stmt = stmt.where(Post.scholar_id == s_id)

    if category:
        stmt = stmt.where(Post.category == category)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern)
            )
        )

    sort_col = Post.created_at
    if sortBy:
        lower = sortBy.lower()
        if lower in ["views", "viewscount", "views_count"]:
            sort_col = Post.views_count
        elif lower in ["likes", "likescount", "likes_count"]:
            sort_col = Post.likes_count
        elif lower in ["comments", "commentscount", "comments_count"]:
            sort_col = Post.comments_count

    if sortOrder.lower() == "asc":
        stmt = stmt.order_by(sort_col.asc())
    else:
        stmt = stmt.order_by(sort_col.desc())

    posts, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_post(p) for p in posts],
        meta=meta
    )


@router.get("/reports", summary="فهرست صفحه‌بندی‌شده گزارش‌های تخلف محتوا")
async def list_reports(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    reason: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(PostReport)

    if status:
        stmt = stmt.where(PostReport.status == status)

    if reason:
        stmt = stmt.where(PostReport.reason == reason)

    stmt = stmt.order_by(PostReport.created_at.desc())

    reports, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_report(r) for r in reports],
        meta=meta
    )


@router.patch("/reports/{id}/status", summary="بررسی و تغییر سریع وضعیت گزارش تخلف")
async def update_report_status(
    id: str,
    body: ReportStatusUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    report = await db.scalar(select(PostReport).where(PostReport.id == id))
    if not report:
        raise HTTPException(status_code=404, detail="گزارش تخلف مورد نظر یافت نشد.")

    report.status = body.status

    # If resolved by removing, also hide the post
    if body.status == "RESOLVED_REMOVED":
        post = await db.scalar(select(Post).where(Post.id == report.post_id))
        if post:
            post.status = "REPORTED_HIDDEN"

    await db.commit()
    await db.refresh(report)

    return success_response(data=serialize_report(report))
