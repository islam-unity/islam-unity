import math
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class UserStatusUpdate(BaseModel):
    is_active: bool


class ThreadStatusUpdate(BaseModel):
    status: str


class ThreadReplyRequest(BaseModel):
    text: str
    sender_role: Optional[str] = "SCHOLAR"
    sender_id: Optional[str] = None
    citation: Optional[str] = None


class ReportStatusUpdate(BaseModel):
    status: str


class ApiKeyStatusUpdate(BaseModel):
    is_active: bool


class ModelPricingUpdate(BaseModel):
    input_cost_per_million_usd: Optional[float] = None
    output_cost_per_million_usd: Optional[float] = None
    cached_cost_per_million_usd: Optional[float] = None
    is_active: Optional[bool] = None


class SectionConfigUpdate(BaseModel):
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    provider: Optional[str] = None
    is_active: Optional[bool] = None
    extra_params: Optional[Dict[str, Any]] = None


async def paginate(
    db: AsyncSession,
    stmt: Select,
    page: int = 1,
    page_size: Optional[int] = None,
    limit: Optional[int] = None,
    count_stmt: Optional[Select] = None
) -> Tuple[List[Any], Dict[str, Any]]:
    # Normalize pagination
    norm_page = max(1, page if page is not None else 1)
    raw_size = page_size if page_size is not None else limit
    norm_page_size = max(1, min(100, raw_size if raw_size is not None else 20))

    if count_stmt is None:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())

    total_count = (await db.scalar(count_stmt)) or 0
    total_pages = math.ceil(total_count / norm_page_size) if total_count > 0 else 0
    offset = (norm_page - 1) * norm_page_size

    paged_stmt = stmt.offset(offset).limit(norm_page_size)
    items = (await db.scalars(paged_stmt)).all()

    meta = {
        "page": norm_page,
        "pageSize": norm_page_size,
        "limit": norm_page_size,
        "totalCount": total_count,
        "total": total_count,
        "totalPages": total_pages,
        "hasMore": (offset + len(items)) < total_count
    }
    return list(items), meta
