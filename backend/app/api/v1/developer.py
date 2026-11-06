from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, Query, Body, Header, Response
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_developer_context
from app.db.models import User, DeveloperAccount, DeveloperApiKey
from app.services.developer_service import DeveloperService
from app.schemas.developer import (
    DeveloperAccountCreateRequest, DeveloperAccountDTO,
    CreateApiKeyRequest, ApiKeyCreatedResponse, ApiKeyDTO,
    DeveloperUsageDTO, OpenAIChatCompletionRequest,
    DeveloperAskRequest, DeveloperRAGSearchRequest,
    DeveloperLibrarySearchRequest, DeveloperBookChatRequest
)
from app.core.response import success_response

router = APIRouter()


# =============================================================================
# 1. Developer Portal & Self-Service Key Management (User JWT Required)
# =============================================================================

@router.post("/account", summary="ایجاد یا دریافت حساب توسعه‌دهنده")
async def create_or_get_account(
    data: Optional[DeveloperAccountCreateRequest] = Body(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    app_name = data.app_name if data else "پروژه معارفی من"
    desc = data.description if data else None
    account = await DeveloperService.get_or_create_account(
        db=db,
        user_id=current_user.id,
        app_name=app_name,
        description=desc
    )
    remaining = max(0, account.monthly_quota_tokens - account.used_tokens_this_month)
    dto = DeveloperAccountDTO(
        id=account.id,
        appName=account.app_name,
        description=account.description,
        tier=account.tier,
        monthlyQuotaTokens=account.monthly_quota_tokens,
        usedTokensThisMonth=account.used_tokens_this_month,
        remainingTokens=remaining,
        rateLimitPerMinute=account.rate_limit_per_minute,
        isActive=account.is_active,
        createdAt=account.created_at.isoformat()
    )
    return success_response(data=dto.model_dump())


@router.get("/account", summary="دریافت وضعیت و مشخصات حساب توسعه‌دهنده")
async def get_developer_account_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account = await DeveloperService.get_or_create_account(db=db, user_id=current_user.id)
    remaining = max(0, account.monthly_quota_tokens - account.used_tokens_this_month)
    dto = DeveloperAccountDTO(
        id=account.id,
        appName=account.app_name,
        description=account.description,
        tier=account.tier,
        monthlyQuotaTokens=account.monthly_quota_tokens,
        usedTokensThisMonth=account.used_tokens_this_month,
        remainingTokens=remaining,
        rateLimitPerMinute=account.rate_limit_per_minute,
        isActive=account.is_active,
        createdAt=account.created_at.isoformat()
    )
    return success_response(data=dto.model_dump())


@router.post("/keys", summary="تولید کلید API اختصاصی جدید (X-API-Key)")
async def generate_api_key(
    data: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account = await DeveloperService.get_or_create_account(db=db, user_id=current_user.id)
    created = await DeveloperService.create_api_key(
        db=db,
        account_id=account.id,
        label=data.label or "کلید اصلی"
    )
    return success_response(data=created.model_dump())


@router.get("/keys", summary="مشاهده فهرست کلیدهای فعال توسعه‌دهنده")
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account = await DeveloperService.get_or_create_account(db=db, user_id=current_user.id)
    keys = await DeveloperService.list_api_keys(db=db, account_id=account.id)
    return success_response(data=[k.model_dump() for k in keys])


@router.delete("/keys/{key_id}", summary="باطل کردن و غیرفعال‌سازی کلید API")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account = await DeveloperService.get_or_create_account(db=db, user_id=current_user.id)
    res = await DeveloperService.revoke_api_key(db=db, account_id=account.id, key_id=key_id)
    return success_response(data={"revoked": res, "keyId": key_id})


@router.get("/usage", summary="گزارش جامع مصرف توکن‌ها و هزینه‌ها")
async def get_developer_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    account = await DeveloperService.get_or_create_account(db=db, user_id=current_user.id)
    usage = await DeveloperService.get_usage_overview(db=db, account_id=account.id)
    return success_response(data=usage.model_dump())


# =============================================================================
# 2. AI Platform Endpoints for Developers (X-API-Key Required)
# =============================================================================

@router.post("/chat/completions", summary="چت هوشمند معارفی سازگار با استاندارد جهانی OpenAI")
async def chat_completions(
    request: OpenAIChatCompletionRequest,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    account, api_key = dev_ctx

    if request.stream:
        return StreamingResponse(
            DeveloperService.stream_chat_completions(
                db=db,
                account=account,
                key=api_key,
                request=request
            ),
            media_type="text/event-stream"
        )

    res = await DeveloperService.chat_completions(
        db=db,
        account=account,
        key=api_key,
        request=request
    )
    return JSONResponse(content=res.model_dump())


@router.post("/ai/ask", summary="پرسش و پاسخ تخصصی معارفی با انتخاب مذهب، لحن و استنادات")
async def ask_religious_question(
    request: DeveloperAskRequest,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    account, api_key = dev_ctx
    res = await DeveloperService.ask_religious(
        db=db,
        account=account,
        key=api_key,
        request=request
    )
    return success_response(data=res.model_dump())


@router.post("/ai/rag-search", summary="کاوش و بازیابی معنایی قطعات اسنادی (کتب، آیات و احادیث)")
async def rag_search_chunks(
    request: DeveloperRAGSearchRequest,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    account, api_key = dev_ctx
    res = await DeveloperService.rag_search(
        db=db,
        account=account,
        key=api_key,
        request=request
    )
    return success_response(data=[r.model_dump() for r in res])


# =============================================================================
# 3. Fast Library Endpoints for Developers (X-API-Key Required)
# =============================================================================

@router.get("/library/books", summary="فهرست و کاتالوگ کتب به همراه فیلتر دسته‌بندی و جستجو")
async def get_library_books(
    categoryId: Optional[str] = Query(None, description="شناسه دسته‌بندی کتب"),
    q: Optional[str] = Query(None, description="عبارت جستجو در عنوان کتاب"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    books_data = await DeveloperService.get_books_catalog(
        db=db,
        category_id=categoryId,
        q=q,
        page=page,
        limit=limit
    )
    return success_response(
        data=[b.model_dump() for b in books_data["items"]],
        meta=books_data.get("meta")
    )


@router.get("/library/books/{book_id}", summary="شناسنامه کتاب و ساختار درختی فصول (TOC)")
async def get_book_details(
    book_id: str,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    book = await DeveloperService.get_book_detail(db=db, book_id=book_id)
    return success_response(data=book)


@router.get("/library/books/{book_id}/chapters/{chapter_id}", summary="متن کامل و قطعات یک فصل")
async def get_chapter_details(
    book_id: str,
    chapter_id: str,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    chapter = await DeveloperService.get_chapter_detail(db=db, book_id=book_id, chapter_id=chapter_id)
    return success_response(data=chapter)


@router.post("/library/search", summary="جستجوی پرسرعت هیبریدی (متنی و برداری) در محتوای کتب")
async def search_library_content(
    request: DeveloperLibrarySearchRequest,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    account, api_key = dev_ctx
    res = await DeveloperService.search_library(
        db=db,
        account=account,
        key=api_key,
        request=request
    )
    return success_response(data=res)


@router.post("/library/books/{book_id}/chat", summary="گفتگوی هوشمند در بستر یک کتاب مشخص")
async def chat_with_specific_book(
    book_id: str,
    request: DeveloperBookChatRequest,
    dev_ctx: Tuple[DeveloperAccount, DeveloperApiKey] = Depends(get_developer_context),
    db: AsyncSession = Depends(get_db)
):
    account, api_key = dev_ctx
    res = await DeveloperService.chat_with_book(
        db=db,
        account=account,
        key=api_key,
        book_id=book_id,
        request=request
    )
    return success_response(data=res)
