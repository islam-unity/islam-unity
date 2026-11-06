from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.db.models import User
from app.services.ai_service import AIService
from app.services.cost_service import CostService
from app.services.llm_provider_service import LLMProviderService
from app.schemas.ai_chat import (
    CreateConversationRequest, SendAIMessageRequest,
    PersonaConfigDTO, MessageFeedbackRequest, UpdateCostConfigRequest,
    SectionModelConfigDTO, UpdateSectionModelConfigRequest,
    BulkUpdateSectionModelConfigRequest, TestModelConnectionRequest,
    TestModelConnectionResponse
)
from app.core.response import success_response

router = APIRouter()


async def _resolve_user_id(current_user: Optional[User], db: AsyncSession) -> str:
    if current_user:
        return current_user.id
    user = await db.scalar(select(User).where(User.id == "usr_seeker_1"))
    if not user:
        user = await db.scalar(select(User).limit(1))
    return user.id if user else "usr_seeker_1"


# 5.0 Direct Quick Chat
@router.post("/chat", summary="گفتگوی سریع با هوش مصنوعی و دریافت پیشنهاد عالم و کتاب متناسب با تخصص")
async def quick_chat(
    data: Dict[str, Any] = Body(...),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = await _resolve_user_id(current_user, db)
    content = data.get("content") or data.get("message") or data.get("query") or ""
    conversation_id = data.get("conversationId")

    if not conversation_id:
        conv_res = await AIService.create_conversation(
            db, user_id, CreateConversationRequest(title=(content[:30] if content else "گفتگوی معارفی"))
        )
        conversation_id = conv_res.conversationId
    else:
        from app.db.models import AIConversation
        conv = await db.scalar(select(AIConversation).where(AIConversation.id == conversation_id))
        if not conv:
            conv = AIConversation(
                id=conversation_id,
                user_id=user_id,
                title=(content[:30] if content else "گفتگوی معارفی")
            )
            db.add(conv)
            await db.commit()

    req = SendAIMessageRequest(
        content=content,
        targetLanguage=data.get("targetLanguage", "fa"),
        overrideModel=data.get("overrideModel") or data.get("model"),
        targetBookId=data.get("targetBookId") or data.get("bookId"),
        targetScholarId=data.get("targetScholarId") or data.get("scholarId"),
        forceScholarEscalation=data.get("forceScholarEscalation") or data.get("forceEscalation")
    )
    resp = await AIService.send_message(db, conversation_id, user_id, req)
    return success_response(data=resp.model_dump())


# 5.1 Chat Conversations
@router.get("/conversations", summary="دریافت لیست جلسات گفتگوی کاربر با هوش مصنوعی")
async def get_conversations(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = await _resolve_user_id(current_user, db)
    convs = await AIService.get_conversations(db, user_id)
    return success_response(data=[c.model_dump() for c in convs])


@router.post("/conversations", summary="ایجاد جلسه گفتگوی جدید")
async def create_conversation(
    data: CreateConversationRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = await _resolve_user_id(current_user, db)
    created = await AIService.create_conversation(db, user_id, data)
    return success_response(data=created.model_dump())


@router.get("/conversations/{conversationId}/messages", summary="دریافت تاریخچه پیام‌های یک گفتگو")
async def get_conversation_messages(
    conversationId: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    messages = await AIService.get_messages(db, conversationId)
    return success_response(data=[m.model_dump() for m in messages])


@router.delete("/conversations/{conversationId}", summary="حذف گفتگو")
async def delete_conversation(
    conversationId: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = await _resolve_user_id(current_user, db)
    res = await AIService.delete_conversation(db, conversationId, user_id)
    return success_response(data=res)


# 5.2 Sending Messages and Streaming
@router.post("/conversations/{conversationId}/messages", summary="ارسال پیام متنی و دریافت پاسخ هوشمند با استنادات قرآنی")
async def send_message(
    conversationId: str,
    data: SendAIMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = await _resolve_user_id(current_user, db)
    resp = await AIService.send_message(db, conversationId, user_id, data)
    return success_response(data=resp.model_dump())


@router.post("/conversations/{conversationId}/stream", summary="استریم زنده پاسخ هوش مصنوعی (Server-Sent Events - SSE)")
async def stream_message(
    conversationId: str,
    data: SendAIMessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = await _resolve_user_id(current_user, db)
    model_override = data.model or data.overrideModel
    return StreamingResponse(
        AIService.stream_ai_response(
            db=db,
            conversation_id=conversationId,
            user_id=user_id,
            content=data.content,
            model_override=model_override,
            target_language=data.targetLanguage,
            exclude_previous_sources=data.excludePreviousSources
        ),
        media_type="text/event-stream"
    )


# 5.3 Persona Customization
@router.get("/persona", summary="دریافت تنظیمات پرسونای دینی و اخلاقی کاربر")
async def get_persona(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    persona = await AIService.get_persona(db, current_user.id)
    return success_response(data=persona.model_dump())


@router.put("/persona", summary="به‌روزرسانی تنظیمات پرسونای کاربر (لحن، رویکرد فقهی، سطح تفصیل)")
async def update_persona(
    data: PersonaConfigDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    updated = await AIService.update_persona(db, current_user.id, data)
    return success_response(data=updated.model_dump())


@router.get("/persona/presets", summary="دریافت فهرست قالب‌های شخصیتی و نقش‌های آماده ربات معارفی")
async def get_persona_presets():
    presets = AIService.get_persona_presets()
    return success_response(data=presets)


# 5.4 Prompt Suggestions
@router.get("/prompt-suggestions", summary="پیشنهادهای هوشمند پرامپت معارفی برای شروع گفتگو متناسب با علایق کاربر")
async def get_prompt_suggestions(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    user_id = current_user.id if current_user else None
    suggestions = await AIService.get_prompt_suggestions(db, user_id=user_id)
    return success_response(data=[s.model_dump() for s in suggestions])


@router.post("/messages/{messageId}/rating", summary="ثبت امتیاز (لایک/دیس‌لایک) و نظر کیفی درباره پاسخ AI")
async def rate_message(
    messageId: str,
    data: MessageFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await AIService.rate_message(db, messageId, data)
    return success_response(data=res)


# 5.5 User Long-Term Memory Management
@router.get("/memory", summary="لیست اطلاعات و ترجیحات فقهی/معارفی به خاطر سپرده شده کاربر")
async def get_user_memories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.agent.memory import MemoryService
    memories = await MemoryService.list_user_memories(db, current_user.id)
    return success_response(data=memories)


@router.delete("/memory/{memoryId}", summary="حذف یک مورد حافظه بلندمدت کاربر")
async def delete_user_memory_item(
    memoryId: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.agent.memory import MemoryService
    deleted_count = await MemoryService.delete_memory(db, current_user.id, memory_id=memoryId)
    return success_response(data={"deleted": deleted_count > 0, "id": memoryId})


@router.delete("/memory", summary="پاک‌سازی کامل تمام موارد حافظه بلندمدت کاربر")
async def clear_all_user_memories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.agent.memory import MemoryService
    deleted_count = await MemoryService.delete_memory(db, current_user.id)
    return success_response(data={"cleared": True, "count": deleted_count})


# 5.6 Token Usage & Cost Management
@router.get("/cost-config", summary="دریافت تنظیمات تعرفه توکن مدل‌ها و نرخ تبدیل دلار به ریال")
async def get_cost_config(
    db: AsyncSession = Depends(get_db)
):
    cfg = await CostService.get_cost_config(db)
    return success_response(data=cfg.model_dump())


@router.put("/cost-config", summary="به‌روزرسانی تعرفه توکن‌های ورودی/خروجی/کش و نرخ دلار به ریال")
async def update_cost_config(
    data: UpdateCostConfigRequest,
    db: AsyncSession = Depends(get_db)
):
    updated = await CostService.update_cost_config(db, data)
    return success_response(data=updated.model_dump())


@router.get("/usage-stats", summary="گزارش جامع کل توکن‌های مصرفی و هزینه‌ها به تفکیک دلار و ریال")
async def get_usage_stats(
    db: AsyncSession = Depends(get_db)
):
    stats = await CostService.get_usage_statistics(db)
    return success_response(data=stats.model_dump())


@router.get("/conversations/{conversationId}/usage", summary="گزارش مصرف توکن و هزینه یک گفتگوی مشخص")
async def get_conversation_usage(
    conversationId: str,
    db: AsyncSession = Depends(get_db)
):
    stats = await CostService.get_usage_statistics(db, conversation_id=conversationId)
    return success_response(data=stats.model_dump())


# 5.7 Per-Section AI Model & Base URL Management
@router.get("/models-config", summary="دریافت پیکربندی مدل‌ها و Base URL تمام بخش‌های سامانه به تفکیک")
async def get_all_models_config(
    db: AsyncSession = Depends(get_db)
):
    """
    لیست تنظیمات مدل، Base URL، کلیدهای دسترسی (ماسک‌شده) و ارائه‌دهنده را برای تمام بخش‌ها برمی‌گرداند:
    - chat (گفتگوی هوشمند)
    - embedding (تولید بردارهای معنایی)
    - agentic_rag (موتور عامل هوشمند و مسیریابی)
    - jev (موتور تصمیم‌گیری سامانه یک)
    - library (چت تخصصی کتب و تحلیل فصول)
    - quran (تدبر و تحلیل هوشمند آیات)
    - consultation (دستیار مشاوران و علما)
    """
    configs = await LLMProviderService.get_all_section_configs(db)
    return success_response(data=[c.model_dump() for c in configs])


@router.put("/models-config", summary="به‌روزرسانی گروهی مدل‌ها و Base URL بخش‌های مختلف")
async def bulk_update_models_config(
    data: BulkUpdateSectionModelConfigRequest,
    db: AsyncSession = Depends(get_db)
):
    updated = await LLMProviderService.bulk_update_section_configs(db, data)
    return success_response(data=[c.model_dump() for c in updated])


@router.get("/models-config/{section}", summary="دریافت پیکربندی مدل و Base URL یک بخش خاص")
async def get_section_model_config(
    section: str,
    db: AsyncSession = Depends(get_db)
):
    cfg_dict = await LLMProviderService.get_section_config(db, section)
    dto = SectionModelConfigDTO(
        sectionKey=cfg_dict["section_key"],
        sectionNameFa=cfg_dict["section_name_fa"],
        descriptionFa=cfg_dict.get("description_fa"),
        modelName=cfg_dict["model_name"],
        baseUrl=cfg_dict.get("base_url"),
        apiKeyMasked=LLMProviderService.mask_api_key(cfg_dict.get("api_key")),
        hasCustomApiKey=cfg_dict.get("has_custom_api_key", False),
        provider=cfg_dict.get("provider", "gemini"),
        isActive=cfg_dict.get("is_active", True),
        extraParams=cfg_dict.get("extra_params"),
        updatedAt=cfg_dict.get("updated_at")
    )
    return success_response(data=dto.model_dump())


@router.put("/models-config/{section}", summary="به‌روزرسانی مدل، Base URL و کلید API یک بخش خاص")
async def update_section_model_config(
    section: str,
    data: UpdateSectionModelConfigRequest,
    db: AsyncSession = Depends(get_db)
):
    updated = await LLMProviderService.update_section_config(db, section, data)
    return success_response(data=updated.model_dump())


@router.post("/models-config/{section}/test", summary="تست اتصال و سنجش زمان تاخیر مدل و Base URL یک بخش")
async def test_section_model_connection(
    section: str,
    data: Optional[TestModelConnectionRequest] = Body(default=None),
    db: AsyncSession = Depends(get_db)
):
    result = await LLMProviderService.test_connection(section, db=db, override=data)
    return success_response(data=result.model_dump())
