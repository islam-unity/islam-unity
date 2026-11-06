from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.models import (
    AIConversation, AIMessage, AIUsageLog, AIModelPricing, AISectionConfig,
    Book, Scholar, User, BookChapter
)
from app.db.session import get_db
from app.api.v1.admin.common import (
    ModelPricingUpdate, SectionConfigUpdate, paginate
)
from app.services.ai_service import AIService
from app.services.agent.memory import MemoryService
from app.schemas.ai_chat import CreateConversationRequest, SendAIMessageRequest
from fastapi import Body

router = APIRouter()


def serialize_conversation(conv: AIConversation) -> Dict[str, Any]:
    return {
        "id": conv.id,
        "userId": conv.user_id,
        "user_id": conv.user_id,
        "title": conv.title,
        "createdAt": conv.created_at.isoformat() if conv.created_at else None,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updatedAt": conv.updated_at.isoformat() if conv.updated_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None
    }


def serialize_ai_message(msg: AIMessage) -> Dict[str, Any]:
    return {
        "id": msg.id,
        "conversationId": msg.conversation_id,
        "conversation_id": msg.conversation_id,
        "role": msg.role,
        "content": msg.content,
        "referencedAyahs": msg.referenced_ayahs or [],
        "referenced_ayahs": msg.referenced_ayahs or [],
        "referencedHadiths": msg.referenced_hadiths or [],
        "referenced_hadiths": msg.referenced_hadiths or [],
        "sources": msg.sources or [],
        "suggestScholarEscalation": msg.suggest_scholar_escalation,
        "suggest_scholar_escalation": msg.suggest_scholar_escalation,
        "escalationCategory": msg.escalation_category,
        "escalation_category": msg.escalation_category,
        "isLiked": msg.is_liked,
        "is_liked": msg.is_liked,
        "feedbackText": msg.feedback_text,
        "feedback_text": msg.feedback_text,
        "tokenUsage": msg.token_usage or {},
        "token_usage": msg.token_usage or {},
        "createdAt": msg.created_at.isoformat() if msg.created_at else None,
        "created_at": msg.created_at.isoformat() if msg.created_at else None
    }


def serialize_usage_log(log: AIUsageLog) -> Dict[str, Any]:
    return {
        "id": log.id,
        "userId": log.user_id,
        "user_id": log.user_id,
        "conversationId": log.conversation_id,
        "conversation_id": log.conversation_id,
        "messageId": log.message_id,
        "message_id": log.message_id,
        "modelName": log.model_name,
        "model_name": log.model_name,
        "promptTokens": log.prompt_tokens,
        "prompt_tokens": log.prompt_tokens,
        "outputTokens": log.output_tokens,
        "output_tokens": log.output_tokens,
        "cachedTokens": log.cached_tokens,
        "cached_tokens": log.cached_tokens,
        "totalTokens": log.total_tokens,
        "total_tokens": log.total_tokens,
        "costUsd": log.cost_usd,
        "cost_usd": log.cost_usd,
        "costIrr": log.cost_irr,
        "cost_irr": log.cost_irr,
        "exchangeRateApplied": log.exchange_rate_applied,
        "exchange_rate_applied": log.exchange_rate_applied,
        "createdAt": log.created_at.isoformat() if log.created_at else None,
        "created_at": log.created_at.isoformat() if log.created_at else None
    }


def serialize_pricing(p: AIModelPricing) -> Dict[str, Any]:
    return {
        "id": p.id,
        "modelName": p.model_name,
        "model_name": p.model_name,
        "inputCostPerMillionUsd": p.input_cost_per_million_usd,
        "input_cost_per_million_usd": p.input_cost_per_million_usd,
        "outputCostPerMillionUsd": p.output_cost_per_million_usd,
        "output_cost_per_million_usd": p.output_cost_per_million_usd,
        "cachedCostPerMillionUsd": p.cached_cost_per_million_usd,
        "cached_cost_per_million_usd": p.cached_cost_per_million_usd,
        "isActive": p.is_active,
        "is_active": p.is_active,
        "updatedAt": p.updated_at.isoformat() if p.updated_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None
    }


def serialize_section_config(sec: AISectionConfig) -> Dict[str, Any]:
    return {
        "sectionKey": sec.section_key,
        "section_key": sec.section_key,
        "sectionNameFa": sec.section_name_fa,
        "section_name_fa": sec.section_name_fa,
        "descriptionFa": sec.description_fa,
        "description_fa": sec.description_fa,
        "modelName": sec.model_name,
        "model_name": sec.model_name,
        "baseUrl": sec.base_url,
        "base_url": sec.base_url,
        "apiKey": sec.api_key,
        "api_key": sec.api_key,
        "provider": sec.provider,
        "isActive": sec.is_active,
        "is_active": sec.is_active,
        "extraParams": sec.extra_params or {},
        "extra_params": sec.extra_params or {},
        "updatedAt": sec.updated_at.isoformat() if sec.updated_at else None,
        "updated_at": sec.updated_at.isoformat() if sec.updated_at else None
    }


@router.get("/conversations", summary="فهرست صفحه‌بندی‌شده سشن‌های گفتگوی هوش مصنوعی")
async def list_conversations(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    user_id: Optional[str] = Query(None),
    userId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AIConversation)

    u_id = user_id or userId
    if u_id:
        stmt = stmt.where(AIConversation.user_id == u_id)

    if search:
        stmt = stmt.where(AIConversation.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(AIConversation.updated_at.desc(), AIConversation.created_at.desc())

    convs, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_conversation(c) for c in convs],
        meta=meta
    )


@router.get("/conversations/{id}/messages", summary="تاریخچه پیام‌های سشن گفتگوی هوش مصنوعی")
async def get_conversation_messages(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    conv = await db.scalar(select(AIConversation).where(AIConversation.id == id))
    if not conv:
        raise HTTPException(status_code=404, detail="سشن گفتگوی هوش مصنوعی یافت نشد.")

    stmt = select(AIMessage).where(AIMessage.conversation_id == id).order_by(AIMessage.created_at.asc())
    messages = (await db.scalars(stmt)).all()

    return success_response(data=[serialize_ai_message(m) for m in messages])


@router.get("/usage-logs", summary="فهرست لاگ‌های مصرف توکن و هزینه‌های هوش مصنوعی")
async def list_usage_logs(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    user_id: Optional[str] = Query(None),
    userId: Optional[str] = Query(None),
    model_name: Optional[str] = Query(None),
    modelName: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AIUsageLog)

    u_id = user_id or userId
    if u_id:
        stmt = stmt.where(AIUsageLog.user_id == u_id)

    m_name = model_name or modelName
    if m_name:
        stmt = stmt.where(AIUsageLog.model_name == m_name)

    s_date = start_date or startDate
    if s_date:
        try:
            dt = datetime.fromisoformat(s_date.replace("Z", "+00:00"))
            stmt = stmt.where(AIUsageLog.created_at >= dt)
        except Exception:
            pass

    e_date = end_date or endDate
    if e_date:
        try:
            dt = datetime.fromisoformat(e_date.replace("Z", "+00:00"))
            stmt = stmt.where(AIUsageLog.created_at <= dt)
        except Exception:
            pass

    stmt = stmt.order_by(AIUsageLog.created_at.desc())

    logs, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_usage_log(l) for l in logs],
        meta=meta
    )


@router.get("/model-pricing", summary="جدول تعرفه توکن مدل‌های هوش مصنوعی")
@router.get("/pricing", summary="جدول تعرفه توکن مدل‌های هوش مصنوعی (آلیاس)")
async def list_model_pricing(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AIModelPricing).order_by(AIModelPricing.id.asc())
    pricings = (await db.scalars(stmt)).all()
    return success_response(data=[serialize_pricing(p) for p in pricings])


@router.put("/model-pricing/{id}", summary="به‌روزرسانی تعرفه توکن مدل هوش مصنوعی")
@router.put("/pricing/{id}", summary="به‌روزرسانی تعرفه توکن مدل هوش مصنوعی (آلیاس)")
async def update_model_pricing(
    id: str,
    body: ModelPricingUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    pricing = await db.scalar(select(AIModelPricing).where(AIModelPricing.id == id))
    if not pricing:
        raise HTTPException(status_code=404, detail="تعرفه مدل مورد نظر یافت نشد.")

    if body.input_cost_per_million_usd is not None:
        pricing.input_cost_per_million_usd = body.input_cost_per_million_usd
    if body.output_cost_per_million_usd is not None:
        pricing.output_cost_per_million_usd = body.output_cost_per_million_usd
    if body.cached_cost_per_million_usd is not None:
        pricing.cached_cost_per_million_usd = body.cached_cost_per_million_usd
    if body.is_active is not None:
        pricing.is_active = body.is_active

    await db.commit()
    await db.refresh(pricing)

    return success_response(data=serialize_pricing(pricing))


@router.get("/sections", summary="پیکربندی ۷ دپارتمان هوش مصنوعی")
async def list_sections(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AISectionConfig).order_by(AISectionConfig.section_key.asc())
    sections = (await db.scalars(stmt)).all()
    return success_response(data=[serialize_section_config(s) for s in sections])


@router.put("/sections/{key}", summary="به‌روزرسانی پیکربندی دپارتمان هوش مصنوعی")
async def update_section_config(
    key: str,
    body: SectionConfigUpdate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    section = await db.scalar(select(AISectionConfig).where(AISectionConfig.section_key == key))
    if not section:
        raise HTTPException(status_code=404, detail="پیکربندی بخش هوش مصنوعی مورد نظر یافت نشد.")

    if body.model_name is not None:
        section.model_name = body.model_name
    if body.base_url is not None:
        section.base_url = body.base_url
    if body.api_key is not None:
        section.api_key = body.api_key
    if body.provider is not None:
        section.provider = body.provider
    if body.is_active is not None:
        section.is_active = body.is_active
    if body.extra_params is not None:
        section.extra_params = body.extra_params

    await db.commit()
    await db.refresh(section)

    return success_response(data=serialize_section_config(section))


@router.get("/conversations/{id}/traces", summary="مشاهده تاریخچه تریس‌های ایجنت در یک گفتگو")
async def list_conversation_traces(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    from app.db.models import AgentTrace
    stmt = select(AgentTrace).where(AgentTrace.conversation_id == id).order_by(AgentTrace.created_at.desc())
    traces = (await db.scalars(stmt)).all()
    return success_response(data=[
        {
            "id": t.id,
            "conversationId": t.conversation_id,
            "userQuery": t.user_query,
            "mode": t.mode,
            "plan": t.plan,
            "toolCalls": t.tool_calls,
            "verification": t.verification,
            "totalLatencyMs": t.total_latency_ms,
            "totalTokens": t.total_tokens,
            "estimatedCostUsd": t.estimated_cost_usd,
            "createdAt": t.created_at.isoformat() if t.created_at else None
        }
        for t in traces
    ])


@router.get("/users/{id}/memories", summary="مشاهده حافظه بلندمدت یک کاربر برای ادمین")
async def list_admin_user_memories(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    from app.services.agent.memory import MemoryService
    memories = await MemoryService.list_user_memories(db, id)
    return success_response(data=memories)


@router.delete("/users/{id}/memories/{memory_id}", summary="حذف یک مورد حافظه کاربر توسط ادمین")
async def delete_admin_user_memory(
    id: str,
    memory_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    from app.services.agent.memory import MemoryService
    count = await MemoryService.delete_memory(db, user_id=id, memory_id=memory_id)
    return success_response(data={"deleted": count > 0, "id": memory_id})


# =============================================================================
# AI Interactive Testing Lab / Playground Endpoints (آزمایشگاه جامع تست هوش مصنوعی)
# =============================================================================

@router.get("/playground/options", summary="دریافت فهرست کتب، اساتید، دپارتمان‌ها و مدل‌های فعال جهت تست")
async def get_playground_options(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # 1. Books
    books_res = await db.execute(select(Book).order_by(Book.title.asc()))
    books = books_res.scalars().all()
    books_list = [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author or "علمای اسلام",
            "categoryId": b.category_id,
            "language": getattr(b, "language", "fa") or "fa",
            "tags": b.tags or []
        }
        for b in books
    ]

    # 2. Scholars
    scholars_res = await db.execute(select(Scholar).order_by(Scholar.name.asc()))
    scholars = scholars_res.scalars().all()
    scholars_list = [
        {
            "id": s.id,
            "name": s.name,
            "title": s.title,
            "specialties": s.specialties or [],
            "madhhab": s.madhhab,
            "rating": s.rating or 4.95
        }
        for s in scholars
    ]
    if not scholars_list:
        from app.services.recommendation_service import FALLBACK_SCHOLARS
        scholars_list = [
            {
                "id": s["id"],
                "name": s["name"],
                "title": s["title"],
                "specialties": s.get("specialties", []),
                "madhhab": "مقارن",
                "rating": 4.95
            }
            for s in FALLBACK_SCHOLARS
        ]

    # 3. Active Models from Pricing
    pricings_res = await db.execute(select(AIModelPricing).where(AIModelPricing.is_active == True))
    pricings = pricings_res.scalars().all()
    models_list = [p.model_name for p in pricings] or ["gemini-1.5-pro", "gemini-1.5-flash", "gpt-4o", "offline-mock"]

    # 4. Departments
    departments = [
        {"key": "فقه مقارن و تقریب", "title": "فقه مقارن و تقریب مذاهب"},
        {"key": "تفسیر و تدبر قرآن", "title": "تفسیر و تدبر قرآن کریم"},
        {"key": "کلام و عقاید اسلامی", "title": "کلام و عقاید اسلامی"},
        {"key": "اخلاق و سیره نبوی", "title": "اخلاق، تربیت و سیره نبوی"},
        {"key": "کتاب‌پژوهی هوشمند", "title": "کتاب‌پژوهی و ارجاعات متون"}
    ]

    return success_response(data={
        "books": books_list,
        "scholars": scholars_list,
        "models": models_list,
        "departments": departments
    })


@router.post("/playground/chat", summary="ارسال پیام تست در محیط شبیه‌ساز با حافظه گفتگو، هدایت به عالم و هدایت به کتاب")
async def playground_chat(
    data: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    # Resolve or create test user
    test_user_id = data.get("userId") or "usr_admin_test"
    user = await db.scalar(select(User).where(User.id == test_user_id))
    if not user:
        first_user = await db.scalar(select(User).limit(1))
        test_user_id = first_user.id if first_user else test_user_id

    content = (data.get("message") or data.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="متن پیام تست نمی‌تواند خالی باشد.")

    conversation_id = data.get("conversationId")
    if not conversation_id:
        conv_res = await AIService.create_conversation(
            db, test_user_id, CreateConversationRequest(title=f"تست: {content[:25]}")
        )
        conversation_id = conv_res.conversationId

    target_book_id = data.get("targetBookId") or None
    target_scholar_id = data.get("targetScholarId") or None
    force_scholar_escalation = bool(data.get("forceScholarEscalation", False))
    model_override = data.get("model") or None
    target_language = data.get("targetLanguage") or "fa"

    req = SendAIMessageRequest(
        content=content,
        targetLanguage=target_language,
        overrideModel=model_override,
        targetBookId=target_book_id,
        targetScholarId=target_scholar_id,
        forceScholarEscalation=force_scholar_escalation
    )

    resp = await AIService.send_message(db, conversation_id, test_user_id, req)

    # Gather memory and audit state for the test lab
    short_term_history = await MemoryService.get_conversation_history(db, conversation_id, limit_recent=10)
    long_term_memories = await MemoryService.list_user_memories(db, test_user_id)
    prev_source_ids = await MemoryService.get_previous_source_ids(db, conversation_id)

    total_msgs_stmt = select(AIMessage).where(AIMessage.conversation_id == conversation_id)
    all_msgs = (await db.scalars(total_msgs_stmt)).all()
    turn_count = len(all_msgs) // 2

    return success_response(data={
        "conversationId": conversation_id,
        "messageId": resp.messageId,
        "reply": resp.content,
        "referencedAyahs": [a.model_dump() for a in resp.referencedAyahs],
        "referencedHadiths": [h.model_dump() for h in resp.referencedHadiths],
        "sources": [s.model_dump() for s in resp.sources],
        "suggestScholarEscalation": resp.suggestScholarEscalation,
        "escalationCategory": resp.escalationCategory,
        "recommendedScholar": resp.recommendedScholar,
        "recommendedBook": resp.recommendedBook,
        "aiCapabilityStatus": resp.aiCapabilityStatus,
        "routingAssessment": resp.routingAssessment,
        "tokenUsage": resp.tokenUsage.model_dump() if resp.tokenUsage else None,
        "latencyBreakdown": resp.latencyBreakdown,
        "timestamp": resp.timestamp,
        "memoryState": {
            "conversationId": conversation_id,
            "turnCount": turn_count,
            "totalMessages": len(all_msgs),
            "shortTermHistory": short_term_history,
            "longTermMemories": long_term_memories,
            "previousSourceIds": prev_source_ids
        }
    })


@router.post("/playground/reset", summary="ایجاد یک جلسه گفتگوی تمیز جدید برای شروع تست با حافظه تازه")
async def playground_reset(
    data: Dict[str, Any] = Body(default={}),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    test_user_id = data.get("userId") or "usr_admin_test"
    user = await db.scalar(select(User).where(User.id == test_user_id))
    if not user:
        first_user = await db.scalar(select(User).limit(1))
        test_user_id = first_user.id if first_user else test_user_id

    title = data.get("title") or "سشن جدید تست هوش مصنوعی"
    conv_res = await AIService.create_conversation(
        db, test_user_id, CreateConversationRequest(title=title)
    )

    return success_response(data={
        "conversationId": conv_res.conversationId,
        "userId": test_user_id,
        "message": "جلسه گفتگوی جدید با موفقیت ایجاد شد و حافظه گفتگو ریست گردید."
    })


