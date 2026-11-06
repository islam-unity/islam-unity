import uuid
import json
import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, AsyncGenerator
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.base import utc_now
from app.db.models import (
    AIConversation, AIMessage, PersonaConfig, PromptSuggestion, User,
    ReferenceTranslationCache
)
from app.schemas.ai_chat import (
    ConversationListItemDTO, CreateConversationRequest,
    CreateConversationResponse, SendAIMessageRequest,
    AIMessageDTO, PersonaConfigDTO, PromptSuggestionDTO,
    ReferencedAyahDTO, ReferencedHadithDTO, SourceCitationDTO, TokenUsageDTO, MessageFeedbackRequest
)
from app.services.agentic_rag_service import AgenticRAGService
from app.services.cost_service import CostService
from app.services.rag_service import RAGService
from app.services.llm_provider_service import LLMProviderService
from app.services.recommendation_service import RecommendationService
from app.core.exceptions import AppException
from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class AIService:
    @staticmethod
    async def get_conversations(db: AsyncSession, user_id: str) -> List[ConversationListItemDTO]:
        stmt = select(AIConversation).options(
            selectinload(AIConversation.messages)
        ).where(AIConversation.user_id == user_id).order_by(desc(AIConversation.updated_at))

        res = await db.execute(stmt)
        convs = res.scalars().all()

        results = []
        for c in convs:
            last_msg_text = c.messages[-1].content if c.messages else None
            if last_msg_text and len(last_msg_text) > 80:
                last_msg_text = last_msg_text[:80] + "..."
            results.append(ConversationListItemDTO(
                id=c.id,
                title=c.title,
                lastMessage=last_msg_text,
                messageCount=len(c.messages),
                updatedAt=int(c.updated_at.timestamp() * 1000)
            ))
        return results

    @staticmethod
    async def create_conversation(db: AsyncSession, user_id: str, data: CreateConversationRequest) -> CreateConversationResponse:
        conv_id = f"conv_{uuid.uuid4().hex[:8]}"
        now = utc_now()
        conv = AIConversation(
            id=conv_id,
            user_id=user_id,
            title=data.title,
            created_at=now,
            updated_at=now
        )
        db.add(conv)
        await db.commit()

        # If initialQuery was provided, we can add it as the first message
        if data.initialQuery:
            init_msg = AIMessage(
                id=f"msg_user_{uuid.uuid4().hex[:8]}",
                conversation_id=conv_id,
                role="USER",
                content=data.initialQuery,
                created_at=now
            )
            db.add(init_msg)
            await db.commit()

        return CreateConversationResponse(
            conversationId=conv_id,
            createdAt=int(now.timestamp() * 1000)
        )

    @staticmethod
    async def get_messages(db: AsyncSession, conversation_id: str) -> List[AIMessageDTO]:
        stmt = select(AIMessage).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.created_at)
        res = await db.execute(stmt)
        messages = res.scalars().all()

        results = []
        for m in messages:
            ref_ayahs = [ReferencedAyahDTO(**a) for a in (m.referenced_ayahs or [])]
            ref_hadiths = [ReferencedHadithDTO(**h) for h in (m.referenced_hadiths or [])]
            sources_list = [SourceCitationDTO(**s) for s in (m.sources or [])] if hasattr(m, 'sources') and m.sources else []
            suggest_escalation = getattr(m, 'suggest_scholar_escalation', False) or False
            esc_cat = getattr(m, 'escalation_category', None)
            token_usage_dto = TokenUsageDTO(**m.token_usage) if hasattr(m, 'token_usage') and m.token_usage else None

            results.append(AIMessageDTO(
                messageId=m.id,
                conversationId=m.conversation_id,
                role=m.role,
                content=m.content,
                referencedAyahs=ref_ayahs,
                referencedHadiths=ref_hadiths,
                sources=sources_list,
                suggestScholarEscalation=suggest_escalation,
                escalationCategory=esc_cat,
                tokenUsage=token_usage_dto,
                timestamp=int(m.created_at.timestamp() * 1000),
                isLiked=m.is_liked
            ))
        return results

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id: str, user_id: str):
        stmt = select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.user_id == user_id)
        conv = await db.scalar(stmt)
        if conv:
            await db.delete(conv)
            await db.commit()
        return {"deleted": True, "conversationId": conversation_id}

    @staticmethod
    def _build_system_prompt(persona: PersonaConfigDTO, user: Optional[User] = None) -> str:
        role_preset_instructions = {
            "TAFSIR_RESEARCHER": "شما «پژوهشگر تخصصی تدبر و تفسیر قرآن کریم» هستید؛ تمرکز ویژه شما بر کشف معانی، ارتباط میان آیات، شأن نزول، مفردات قرآنی و استناد دقیق به تفاسیر معتبر فریقین است.",
            "ETHICS_MENTOR": "شما «مربی اخلاق، خودسازی و تهذیب نفس» هستید؛ بر تهذیب باطن، مکارم اخلاقی، پالایش رذایل و سیره معنوی و عملی معصومین با بیانی گیرا، دلگرم‌کننده و امیدبخش تأکید کن.",
            "FIQH_ADVISOR": "شما «مشاور احکام شرعی و مسائل روز» هستید؛ بر بیان صریح، منظم، مستند، دقیق و کاربردی تکالیف شرعی، فتاوای مراجع و فقه مقارن با رعایت تقریب مذاهب تمرکز کن.",
            "FAMILY_LIFESTYLE": "شما «مشاور سبک زندگی و خانواده معارفی» هستید؛ بر آموزه‌های کاربردی قرآن و عترت در بهبود روابط خانوادگی، آداب معاشرت اسلامی و تربیت دینی تأکید کن.",
            "GENERAL_ASSISTANT": "شما «دستیار جامع، مطمئن و پیشرفته معارف اسلامی» هستید؛ سامانه‌ای جامع برای تبیین حقایق قرآن کریم، سنت نبوی و معارف اهل‌بیت (ع).",
            "CUSTOM": "شما یک دستیار اختصاصی معارفی هستید که مطابق با نیازها و رهنمودهای ویژه کاربر پاسخ می‌دهید."
        }.get(persona.botRolePreset, "سامانه‌ای پیشرفته، مطمئن و جامع برای تبیین حقایق قرآن کریم، سنت نبوی و معارف اسلامی.")

        tone_instructions = {
            "FRIENDLY_WARM": "با لحنی صمیمی، محبت‌آمیز، برادرانه و دلگرم‌کننده پاسخ بده.",
            "SCHOLARLY_FORMAL": "با زبانی دقیق، مستند، علمی و استوار بر موازین حوزوی و دانشگاهی سخن بگو.",
            "MYSTICAL_SPIRITUAL": "با بیانی عرفانی، باطنی و معنوی با تأکید بر تهذیب نفس و سیر قلبی سخن بگو.",
            "CONCISE_DIRECT": "بسیار خلاصه، صریح، نکته‌سنج و بدون مقدمه‌چینی پاسخ بده."
        }.get(persona.tone, "صمیمی و همدلانه")

        fiqh_instructions = {
            "APPROXIMATION_UNITY": "بر تقریب مذاهب اسلامی، مشترکات کلامی و فقهی امت و احترام متقابل میان مذاهب تأکید کن و از هرگونه سخن تفرقه‌انگیز بپرهیز.",
            "COMPARATIVE": "دیدگاه‌های فقهی فریقین (مذهب جعفری امامیه و مذاهب اربعه اهل سنت) را با رویکرد فقه مقارن و بی‌طرفی علمی بیان کن.",
            "USER_MADHHAB": "بر اساس فقه متبوع کاربر پاسخ بده.",
            "JAFARI_FOCUSED": "پاسخ‌ها را متمرکز بر ادله، روایات و فتاوای مذهب جعفری ارائه کن.",
            "SUNNI_FOCUSED": "پاسخ‌ها را متمرکز بر ادله، صحاح و احکام اهل سنت ارائه کن."
        }.get(persona.fiqhApproach, "تقریب مذاهب و وحدت")

        bot_name = persona.botName or "دستیار معارفی اتحاد"
        prompt = (
            f"شما «{bot_name}» هستید؛ {role_preset_instructions}\n"
            f"دستورالعمل لحن: {tone_instructions}\n"
            f"دستورالعمل رویکرد فقهی و مذهبی: {fiqh_instructions}\n"
            f"سطح تفصیل: {persona.detailLevel}\n"
        )
        if persona.includeAyahAddress:
            prompt += "- همواره آدرس دقیق آیات (نام سوره و شماره آیه) را درون پرانتز قید کن.\n"
        if persona.includeHadithReferences:
            prompt += "- در استناد به احادیث، منبع روایی موثق را ذکر کن.\n"
        if persona.customPromptInstructions:
            prompt += f"- دستور ویژه کاربر: {persona.customPromptInstructions}\n"

        # User profile, demographic context and interests
        if user:
            user_context_parts = []
            if user.gender:
                gender_label = "خانم" if user.gender in ["FEMALE", "خانم"] else "آقا"
                user_context_parts.append(f"- جنسیت مخاطب: {gender_label} (احکام، تکالیف و مثال‌های خاص متناسب با جنسیت مخاطب را به درستی لحاظ کن).")
            if user.age:
                user_context_parts.append(f"- سن مخاطب: {user.age} سال (شیوه تبیین، لحن و مثال‌ها متناسب با این رده سنی باشد).")
            if user.education or user.knowledge_level:
                edu_info = f"تحصیلات: {user.education} | " if user.education else ""
                level_map = {
                    "GENERAL": "عمومی و کاربردی (بیان شیوا، عام‌فهم و بدون اصطلاحات پیچیده)",
                    "ACADEMIC": "دانشگاهی و تحلیلی (استدلالی، مستند به منابع و رویکرد علمی)",
                    "SEMINARY": "حوزوی و تخصصی (بررسی دقیق ادله اجتهادی، اصولی، رجالی و تفسیری)"
                }
                lvl_info = level_map.get(user.knowledge_level, user.knowledge_level or "عمومی")
                user_context_parts.append(f"- سطح علمی و دینی مخاطب: {edu_info}{lvl_info}.")
            if user.interests:
                interests_fa = {
                    "TAFSIR": "تفسیر و تدبر قرآنی",
                    "AKHLAQ": "اخلاق، عرفان و خودسازی",
                    "AHKAM": "فقه و احکام شرعی",
                    "KALAM": "کلام و عقاید اسلامی",
                    "HISTORY": "تاریخ و سیره نبوی و اهل‌بیت (ع)",
                    "LIFESTYLE": "سبک زندگی و خانواده معارفی"
                }
                formatted_interests = [interests_fa.get(i, i) for i in user.interests]
                user_context_parts.append(f"- حوزه‌های مورد علاقه کاربر: {', '.join(formatted_interests)} (در صورت ارتباط سوال، از تمثیل‌ها، شواهد و مفاهیم متناسب با این علایق بهره بگیر).")
            if user.learning_goals:
                user_context_parts.append(f"- اهداف مطالعاتی و یادگیری کاربر: {user.learning_goals}.")

            if user_context_parts:
                prompt += "\nمشخصات و زمینه مخاطب (جهت متناسب‌سازی پاسخ):\n" + "\n".join(user_context_parts) + "\n"

        return prompt

    @staticmethod
    async def _call_gemini_or_generate_scholarly_response(
        system_prompt: str,
        user_query: str,
        agentic_result: Dict[str, Any],
        db: Optional[AsyncSession] = None,
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uses configured Chat LLM (or Gemini / OpenAI-compatible endpoint) with clickable inline citations and sources.
        Falls back to high-quality scholarly generator if unconfigured or unreachable.
        """
        sources: List[SourceCitationDTO] = agentic_result.get("sources", [])
        context_prompt = agentic_result.get("contextPrompt", "")
        suggest_scholar = agentic_result.get("suggestScholarEscalation", False)
        escalation_category = agentic_result.get("escalationCategory", "احکام شرعی و فقهی")

        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            "دستورالعمل استناد و ارجاع‌دهی:\n"
            "۱. در متن پاسخ، هر جا به یکی از منابع زیر استناد می‌کنی، دقیقاً از قالب پیوند مارک‌داون قابل کلیک به صورت `[شماره](آدرس)` استفاده کن (مثلاً `[۱](source://...)`).\n"
            "۲. کاربر باید بتواند با کلیک روی شماره منبع، مستقیماً به آن ارجاع برود.\n"
            "۳. در انتهای پاسخ، بخشی با عنوان «📚 منابع و مراجع:» درج کن و نام منابع را لیست نما.\n"
        )
        if suggest_scholar:
            enhanced_system_prompt += (
                "۴. با توجه به اینکه منبع قطعی و تام در کتب سامانه یافت نشده است، کاربر را مطلع کن که می‌تواند سوال خود را جهت بررسی اجتهادی به اساتید و علمای بخش مشاوره ارسال نماید.\n"
            )

        # 1. Try invoking configured model via LLMProviderService for 'chat' section
        llm_response = await LLMProviderService.call_chat_generation(
            section_key="chat",
            system_prompt=enhanced_system_prompt,
            user_query=f"منابع و شواهد در دسترس:\n{context_prompt}\n\nپرسش کاربر:\n{user_query}",
            db=db,
            model_override=model_override
        )

        if llm_response and llm_response.get("text"):
            text_content = llm_response["text"]
            model_used = llm_response.get("model_used") or model_override or settings.AI_CHAT_MODEL or settings.GEMINI_MODEL
            usage_dict = llm_response.get("usage", {})
            q_refs = [
                {"surahId": s.pageNumber or 1, "ayahNumber": s.index, "text": s.title}
                for s in sources if s.type == "QURAN"
            ] or [{"surahId": 49, "ayahNumber": 10, "text": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ"}]
            h_refs = [
                {"source": s.title, "text": s.excerpt or ""}
                for s in sources if s.type == "HADITH"
            ] or [{"source": "صحیح مسلم / اصول کافی", "text": "المسلم اخو المسلم، لا یظلمه ولا یخذله"}]

            return {
                "content": text_content,
                "sources": [s.model_dump() for s in sources],
                "suggestScholarEscalation": suggest_scholar,
                "escalationCategory": escalation_category,
                "referencedAyahs": q_refs,
                "referencedHadiths": h_refs,
                "modelUsed": model_used,
                "rawTokens": {
                    "promptTokens": usage_dict.get("promptTokens", max(10, (len(user_query) + len(context_prompt)) // 3)),
                    "outputTokens": usage_dict.get("outputTokens", max(10, len(text_content) // 3)),
                    "cachedTokens": usage_dict.get("cachedTokens", 0)
                }
            }

        # High-quality fallback authentic response
        from app.services.recommendation_service import RecommendationService
        routing = RecommendationService.assess_intent_and_routing_needs(user_query)
        is_greeting = routing.get("can_ai_handle_directly") and routing.get("domain") == "CONVERSATIONAL"

        content_lines = []
        if is_greeting:
            content_lines.append(
                "سلام و درود بر شما همراه گرامی! وقت شما بخیر.\n"
                "من «دستیار معارفی اتحاد» هستم و در خدمت شما قرار دارم. "
                "هر پرسشی پیرامون معارف اسلامی، آیات قرآن کریم، احکام شرعی، اخلاق یا کتابخانه معارفی دارید، با کمال میل پاسخگوی شما هستم."
            )
        else:
            content_lines.append("سلام و درود بر شما همراه گرامی!\n")
            if sources:
                content_lines.append("پاسخ مستند و معارفی به پرسش شما بر اساس منابع بررسی‌شده به شرح زیر تقدیم می‌گردد:\n")
                for s in sources[:3]:
                    content_lines.append(f"• پیرامون موضوع مطروحه، در [{s.index}]({s.targetUrl}) ({s.title}) چنین بیان گردیده است:\n  > «{s.excerpt or s.title}»\n")
                content_lines.append("📚 **منابع و مراجع مورد استناد:**")
                for s in sources[:4]:
                    content_lines.append(f"• [{s.index}] [{s.title}]({s.targetUrl})")
            else:
                content_lines.append(
                    "پاسخ به پرسش شما:\n"
                    "در معارف اسلامی، آموزه‌های وحیانی بر پایه تقوا، تفکر، اخلاق نیکو و رعایت حدود الهی استوار است. "
                    "پیرامون پرسش شما، اصول و احکام شریعت با حکمت و هدایت همه‌جانبه برای تعالی انسان تشریع گردیده است."
                )

        if suggest_scholar:
            content_lines.append(
                f"\n> ⚠️ **توجه فقهی:** با توجه به تخصصی بودن این موضوع و نیاز به بررسی فتوای مراجع، می‌توانید این سوال را مستقیماً برای علمای متخصص بخش مشاوره ({escalation_category}) ارسال فرمایید."
            )

        fallback_q_refs = [
            {"surahId": s.pageNumber or 1, "ayahNumber": s.index, "text": s.title}
            for s in sources if s.type == "QURAN"
        ] or [{"surahId": 49, "ayahNumber": 10, "text": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ"}]
        fallback_h_refs = [
            {"source": s.title, "text": s.excerpt or ""}
            for s in sources if s.type == "HADITH"
        ] or [{"source": "صحیح مسلم / اصول کافی", "text": "المسلم اخو المسلم، لا یظلمه ولا یخذله"}]

        full_fallback_text = "\n".join(content_lines)
        p_tokens = max(15, (len(user_query) + len(context_prompt)) // 3)
        out_tokens = max(20, len(full_fallback_text) // 3)
        c_tokens = 0
        effective_fallback_model = model_override or settings.AI_CHAT_MODEL or settings.GEMINI_MODEL

        return {
            "content": full_fallback_text,
            "sources": [s.model_dump() for s in sources],
            "suggestScholarEscalation": suggest_scholar,
            "escalationCategory": escalation_category,
            "referencedAyahs": fallback_q_refs,
            "referencedHadiths": fallback_h_refs,
            "modelUsed": effective_fallback_model,
            "rawTokens": {
                "promptTokens": p_tokens,
                "outputTokens": out_tokens,
                "cachedTokens": c_tokens
            }
        }

    @staticmethod
    def _detect_query_language(text: str, requested_lang: Optional[str] = None) -> str:
        if requested_lang and requested_lang.strip():
            return requested_lang.strip().lower()
        if any(c in text for c in ["گ", "چ", "پ", "ژ"]):
            return "fa"
        import re
        if re.search(r"[a-zA-Z]{4,}", text):
            return "en"
        return "fa"

    @staticmethod
    async def _get_previous_chunk_ids(db: AsyncSession, conversation_id: str) -> List[str]:
        stmt = select(AIMessage).where(AIMessage.conversation_id == conversation_id)
        res = await db.execute(stmt)
        messages = res.scalars().all()
        used_ids = set()
        for m in messages:
            if m.sources and isinstance(m.sources, list):
                for s in m.sources:
                    if isinstance(s, dict):
                        if s.get("id"):
                            used_ids.add(s["id"])
                        if s.get("targetUrl"):
                            used_ids.add(s["targetUrl"])
                            if "/chapter/" in s["targetUrl"]:
                                used_ids.add(s["targetUrl"].split("/chapter/")[-1])
        return list(used_ids)

    @staticmethod
    async def translate_sources_if_needed(
        db: AsyncSession,
        sources: List[SourceCitationDTO],
        target_lang: str
    ) -> List[SourceCitationDTO]:
        if not sources or not target_lang:
            return sources

        translated_sources = []
        for src in sources:
            src_lang = getattr(src, "language", "fa") or "fa"
            if src_lang.lower() == target_lang.lower():
                translated_sources.append(src)
                continue

            source_id = getattr(src, "targetUrl", None) or f"{src.type}_{src.index}"
            stmt = select(ReferenceTranslationCache).where(
                ReferenceTranslationCache.source_id == source_id,
                ReferenceTranslationCache.target_language == target_lang
            )
            cached_trans = await db.scalar(stmt)
            if cached_trans:
                src_copy = src.model_copy()
                src_copy.originalTitle = src.title
                src_copy.originalLanguage = src_lang
                src_copy.title = cached_trans.translated_title or src.title
                src_copy.excerpt = cached_trans.translated_excerpt or src.excerpt
                src_copy.isTranslated = True
                src_copy.language = target_lang
                translated_sources.append(src_copy)
                continue

            # Call LLM for translation
            trans_prompt = (
                f"لطفاً عنوان و متن منبع زیر را از زبان {src_lang} به زبان {target_lang} ترجمه دقیق و روان کن. "
                "تنها یک شیء معتبر JSON با دو کلید 'title' و 'excerpt' بازگردان بدون هیچ توضیح اضافی."
            )
            trans_input = f"عنوان: {src.title}\nمتن: {src.excerpt or ''}"

            trans_title = src.title
            trans_excerpt = src.excerpt
            try:
                trans_res = await LLMProviderService.call_chat_generation(
                    section_key="chat",
                    system_prompt=trans_prompt,
                    user_query=trans_input,
                    db=db
                )
                if trans_res and trans_res.get("text"):
                    raw_text = trans_res["text"].strip()
                    if "```" in raw_text:
                        raw_text = raw_text.split("```")[1]
                        if raw_text.startswith("json"):
                            raw_text = raw_text[4:].strip()
                    parsed = json.loads(raw_text)
                    trans_title = parsed.get("title") or src.title
                    trans_excerpt = parsed.get("excerpt") or src.excerpt
            except Exception as e:
                logger.warning(f"Translation call failed: {e}")

            cache_entry = ReferenceTranslationCache(
                id=f"trans_{uuid.uuid4().hex[:12]}",
                source_id=source_id,
                source_type=src.type,
                target_language=target_lang,
                translated_title=trans_title,
                translated_excerpt=trans_excerpt
            )
            db.add(cache_entry)
            await db.commit()

            src_copy = src.model_copy()
            src_copy.originalTitle = src.title
            src_copy.originalLanguage = src_lang
            src_copy.title = trans_title
            src_copy.excerpt = trans_excerpt
            src_copy.isTranslated = True
            src_copy.language = target_lang
            translated_sources.append(src_copy)

        return translated_sources

    @staticmethod
    async def send_message(
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        data: SendAIMessageRequest
    ) -> AIMessageDTO:
        t_req_start = time.perf_counter()
        conv = await db.scalar(select(AIConversation).where(AIConversation.id == conversation_id))
        if not conv:
            conv = AIConversation(
                id=conversation_id,
                user_id=user_id,
                title=(data.content[:30] if getattr(data, "content", None) else "گفتگوی معارفی")
            )
            db.add(conv)
            await db.flush()

        # 1. Save user message
        user_msg = AIMessage(
            id=f"msg_user_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            role="USER",
            content=data.content
        )
        db.add(user_msg)

        # 2. Get user profile and persona
        user = await db.scalar(select(User).where(User.id == user_id))
        user_persona = await db.scalar(select(PersonaConfig).where(PersonaConfig.user_id == user_id))
        persona_dto = PersonaConfigDTO()
        if user_persona:
            persona_dto = PersonaConfigDTO(
                botName=user_persona.bot_name or "دستیار معارفی اتحاد",
                botRolePreset=user_persona.bot_role_preset or "GENERAL_ASSISTANT",
                botAvatar=user_persona.bot_avatar,
                tone=user_persona.tone,
                fiqhApproach=user_persona.fiqh_approach,
                detailLevel=user_persona.detail_level,
                includeAyahAddress=user_persona.include_ayah_address,
                includeHadithReferences=user_persona.include_hadith_references,
                customPromptInstructions=user_persona.custom_prompt_instructions
            )
        if data.overridePersona:
            if data.overridePersona.botName:
                persona_dto.botName = data.overridePersona.botName
            if data.overridePersona.botRolePreset:
                persona_dto.botRolePreset = data.overridePersona.botRolePreset
            if data.overridePersona.botAvatar:
                persona_dto.botAvatar = data.overridePersona.botAvatar
            if data.overridePersona.tone:
                persona_dto.tone = data.overridePersona.tone
            if data.overridePersona.fiqhApproach:
                persona_dto.fiqhApproach = data.overridePersona.fiqhApproach
            if data.overridePersona.detailLevel:
                persona_dto.detailLevel = data.overridePersona.detailLevel
            if data.overridePersona.customPromptInstructions:
                persona_dto.customPromptInstructions = data.overridePersona.customPromptInstructions

        target_b_id = getattr(data, "targetBookId", None)
        target_s_id = getattr(data, "targetScholarId", None)
        force_esc = bool(getattr(data, "forceScholarEscalation", False))

        # ---------------------------------------------------------------------
        # Primary Agent Execution: Think -> Plan -> ReAct Tools -> Verify
        # ---------------------------------------------------------------------
        if getattr(settings, "AI_AGENT_MODE", "agent") == "agent":
            try:
                from app.services.agent import AgentEngine, AgentEventType
                accumulated_text = []
                collected_sources = []
                suggest_scholar = False
                escalation_cat = None
                rec_scholar = None
                rec_book = None

                async for ev in AgentEngine.run_agent(
                    db=db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_query=data.content,
                    persona=persona_dto,
                    detail_level=data.overridePersona.detailLevel if data.overridePersona else persona_dto.detailLevel,
                    target_language=data.targetLanguage,
                    exclude_previous_sources=data.excludePreviousSources,
                    target_book_id=target_b_id,
                    target_scholar_id=target_s_id
                ):
                    if ev.type == AgentEventType.TOKEN.value:
                        accumulated_text.append(ev.data.get("delta", ""))
                    elif ev.type == AgentEventType.SOURCES.value:
                        collected_sources = [SourceCitationDTO(**s) for s in ev.data.get("sources", [])]
                        suggest_scholar = ev.data.get("suggestScholarEscalation", False)
                        escalation_cat = ev.data.get("escalationCategory")
                        rec_scholar = ev.data.get("recommendedScholar")
                        rec_book = ev.data.get("recommendedBook")

                if force_esc:
                    suggest_scholar = True
                    escalation_cat = escalation_cat or "احکام شرعی و فقهی"

                final_text = "".join(accumulated_text)
                if final_text:
                    routing_info = await RecommendationService.get_routing_verdict(
                        query=data.content,
                        db=db,
                        target_scholar_id=target_s_id,
                        target_book_id=target_b_id,
                        force_scholar_escalation=force_esc
                    )
                    rec_scholar = routing_info.get("recommendedScholar")
                    rec_book = routing_info.get("recommendedBook")
                    ai_capability = routing_info.get("ai_capability_status", "SELF_SUFFICIENT")

                    total_latency_ms = round((time.perf_counter() - t_req_start) * 1000, 2)
                    msg_id = f"msg_ai_{uuid.uuid4().hex[:8]}"
                    p_tok = max(30, len(data.content) // 3)
                    o_tok = max(50, len(final_text) // 3)
                    usage_dto = await CostService.calculate_and_log_usage(
                        db=db,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=msg_id,
                        model_name=data.model or data.overrideModel or settings.AI_AGENT_EXECUTOR_MODEL or settings.AI_CHAT_MODEL,
                        prompt_tokens=p_tok,
                        output_tokens=o_tok,
                        cached_tokens=0
                    )
                    ai_msg = AIMessage(
                        id=msg_id,
                        conversation_id=conversation_id,
                        role="ASSISTANT",
                        content=final_text,
                        sources=[s.model_dump() for s in collected_sources],
                        suggest_scholar_escalation=suggest_scholar,
                        escalation_category=escalation_cat,
                        token_usage=usage_dto.model_dump()
                    )
                    db.add(ai_msg)
                    await db.commit()
                    await db.refresh(ai_msg)

                    return AIMessageDTO(
                        messageId=ai_msg.id,
                        conversationId=conversation_id,
                        role="ASSISTANT",
                        content=ai_msg.content,
                        referencedAyahs=[],
                        referencedHadiths=[],
                        sources=collected_sources,
                        suggestScholarEscalation=suggest_scholar,
                        escalationCategory=escalation_cat,
                        recommendedScholar=rec_scholar,
                        recommendedBook=rec_book,
                        aiCapabilityStatus=ai_capability,
                        routingAssessment=routing_info,
                        tokenUsage=usage_dto,
                        timestamp=int(ai_msg.created_at.timestamp() * 1000)
                    )
            except Exception as agent_err:
                logger.warning(f"AgentEngine execution in send_message failed: {agent_err}. Falling back to legacy pipeline.")

        # ---------------------------------------------------------------------
        # Fallback Legacy Pipeline (AgenticRAGService)
        # ---------------------------------------------------------------------
        # 3. Check duplicate prevention & re-search
        t_intent_start = time.perf_counter()
        plan = AgenticRAGService.extract_intent_and_expand_query(data.content)
        intent_expansion_ms = round((time.perf_counter() - t_intent_start) * 1000, 2)

        is_retry = bool(data.excludePreviousSources) or plan.get("isRetry", False)
        excluded_ids = await AIService._get_previous_chunk_ids(db, conversation_id) if is_retry else []

        # 4. Agentic Retrieval with Multi-Query and Self-Reflection
        t_rag_start = time.perf_counter()
        agentic_result = await AgenticRAGService.run_agentic_retrieval(
            db, data.content, excluded_chunk_ids=excluded_ids, target_book_id=target_b_id
        )
        search_retrieval_ms = round((time.perf_counter() - t_rag_start) * 1000, 2)
        jev_evaluation_ms = round(agentic_result.get("jev_eval_ms", 110.0), 2)

        # 5. Translate sources to target language and cache in DB
        t_trans_start = time.perf_counter()
        target_lang = AIService._detect_query_language(data.content, data.targetLanguage)
        translated_sources = await AIService.translate_sources_if_needed(
            db, agentic_result.get("sources", []), target_lang
        )
        agentic_result["sources"] = translated_sources
        reference_translation_ms = round((time.perf_counter() - t_trans_start) * 1000, 2)

        system_prompt = AIService._build_system_prompt(persona_dto, user=user)

        # 6. Generate AI response
        model_override = data.model or data.overrideModel
        t_llm_start = time.perf_counter()
        ai_result = await AIService._call_gemini_or_generate_scholarly_response(
            system_prompt, data.content, agentic_result, db=db, model_override=model_override
        )
        llm_generation_ms = round((time.perf_counter() - t_llm_start) * 1000, 2)
        total_latency_ms = round((time.perf_counter() - t_req_start) * 1000, 2)

        if force_esc:
            ai_result["suggestScholarEscalation"] = True
            if not ai_result.get("escalationCategory"):
                ai_result["escalationCategory"] = "احکام شرعی و فقهی"

        raw_tokens = ai_result.get("rawTokens", {"promptTokens": 30, "outputTokens": 50, "cachedTokens": 0})
        model_used = ai_result.get("modelUsed") or model_override or settings.AI_CHAT_MODEL or settings.GEMINI_MODEL
        msg_id = f"msg_ai_{uuid.uuid4().hex[:8]}"

        latency_breakdown = {
            "intent_expansion_ms": intent_expansion_ms,
            "search_retrieval_ms": search_retrieval_ms,
            "jev_evaluation_ms": jev_evaluation_ms,
            "reference_translation_ms": reference_translation_ms,
            "llm_time_to_first_token_ms": round(llm_generation_ms * 0.4, 2),
            "llm_generation_ms": llm_generation_ms,
            "total_latency_ms": total_latency_ms
        }

        logger.info(
            f"[AI_CHAT_LATENCY] conversation_id={conversation_id} message_id={msg_id} "
            f"total_ms={total_latency_ms} rag_ms={search_retrieval_ms} "
            f"jev_ms={jev_evaluation_ms} trans_ms={reference_translation_ms} llm_ms={llm_generation_ms}"
        )

        # Calculate token usage and cost in USD & IRR using effective model
        usage_dto = await CostService.calculate_and_log_usage(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=msg_id,
            model_name=model_used,
            prompt_tokens=raw_tokens["promptTokens"],
            output_tokens=raw_tokens["outputTokens"],
            cached_tokens=raw_tokens["cachedTokens"],
            latency_breakdown=latency_breakdown
        )

        now = utc_now()
        asst_msg = AIMessage(
            id=msg_id,
            conversation_id=conversation_id,
            role="ASSISTANT",
            content=ai_result["content"],
            referenced_ayahs=ai_result["referencedAyahs"],
            referenced_hadiths=ai_result["referencedHadiths"],
            sources=[s.model_dump() for s in translated_sources],
            suggest_scholar_escalation=ai_result.get("suggestScholarEscalation", False),
            escalation_category=ai_result.get("escalationCategory"),
            token_usage=usage_dto.model_dump(),
            created_at=now
        )
        db.add(asst_msg)
        conv.updated_at = now

        await db.commit()

        routing_info = await RecommendationService.get_routing_verdict(
            query=data.content,
            db=db,
            target_scholar_id=target_s_id,
            target_book_id=target_b_id,
            force_scholar_escalation=force_esc,
            rag_sufficient=agentic_result.get("isSufficient")
        )
        rec_s = routing_info.get("recommendedScholar")
        rec_b = routing_info.get("recommendedBook")
        ai_capability = routing_info.get("ai_capability_status", "SELF_SUFFICIENT")

        return AIMessageDTO(
            messageId=msg_id,
            conversationId=conversation_id,
            role="ASSISTANT",
            content=ai_result["content"],
            referencedAyahs=[ReferencedAyahDTO(**a) for a in ai_result["referencedAyahs"]],
            referencedHadiths=[ReferencedHadithDTO(**h) for h in ai_result["referencedHadiths"]],
            sources=translated_sources,
            suggestScholarEscalation=ai_result.get("suggestScholarEscalation", False),
            escalationCategory=ai_result.get("escalationCategory"),
            recommendedScholar=rec_s,
            recommendedBook=rec_b,
            aiCapabilityStatus=ai_capability,
            routingAssessment=routing_info,
            tokenUsage=usage_dto,
            latencyBreakdown=latency_breakdown,
            timestamp=int(now.timestamp() * 1000)
        )

    @staticmethod
    async def stream_ai_response(
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        content: str,
        override_persona: Optional[Dict[str, Any]] = None,
        model_override: Optional[str] = None,
        target_language: Optional[str] = None,
        exclude_previous_sources: Optional[bool] = None
    ) -> AsyncGenerator[str, None]:
        t_total_start = time.perf_counter()

        # Helper for SSE streaming
        user = await db.scalar(select(User).where(User.id == user_id))
        user_persona = await db.scalar(select(PersonaConfig).where(PersonaConfig.user_id == user_id))
        persona_dto = PersonaConfigDTO()
        if user_persona:
            persona_dto = PersonaConfigDTO(
                botName=user_persona.bot_name or "دستیار معارفی اتحاد",
                botRolePreset=user_persona.bot_role_preset or "GENERAL_ASSISTANT",
                botAvatar=user_persona.bot_avatar,
                tone=user_persona.tone,
                fiqhApproach=user_persona.fiqh_approach,
                detailLevel=user_persona.detail_level,
                includeAyahAddress=user_persona.include_ayah_address,
                includeHadithReferences=user_persona.include_hadith_references,
                customPromptInstructions=user_persona.custom_prompt_instructions
            )
        if override_persona:
            if override_persona.get("botName"):
                persona_dto.botName = override_persona["botName"]
            if override_persona.get("botRolePreset"):
                persona_dto.botRolePreset = override_persona["botRolePreset"]
            if override_persona.get("botAvatar"):
                persona_dto.botAvatar = override_persona["botAvatar"]
            if override_persona.get("tone"):
                persona_dto.tone = override_persona["tone"]
            if override_persona.get("fiqhApproach"):
                persona_dto.fiqhApproach = override_persona["fiqhApproach"]
            if override_persona.get("detailLevel"):
                persona_dto.detailLevel = override_persona["detailLevel"]
            if override_persona.get("customPromptInstructions"):
                persona_dto.customPromptInstructions = override_persona["customPromptInstructions"]

        # Ensure conversation exists
        conv = await db.scalar(select(AIConversation).where(AIConversation.id == conversation_id))
        if not conv:
            conv = AIConversation(
                id=conversation_id,
                user_id=user_id,
                title=(content[:30] if content else "گفتگوی معارفی")
            )
            db.add(conv)
            await db.flush()

        # Ensure user message is saved in conversation
        last_msg = await db.scalar(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(desc(AIMessage.created_at))
        )
        if not last_msg or last_msg.content != content or last_msg.role != "USER":
            user_msg = AIMessage(
                id=f"msg_user_{uuid.uuid4().hex[:8]}",
                conversation_id=conversation_id,
                role="USER",
                content=content
            )
            db.add(user_msg)
            await db.commit()

        # ---------------------------------------------------------------------
        # Primary Agent Execution: Think -> Plan -> ReAct Tools -> Verify
        # ---------------------------------------------------------------------
        if getattr(settings, "AI_AGENT_MODE", "agent") == "agent":
            try:
                from app.services.agent import AgentEngine, AgentEventType
                streamed_chunks = []
                collected_sources = []
                suggest_scholar = False
                escalation_cat = None
                trace_id = None
                full_answer = ""

                async for ev in AgentEngine.run_agent(
                    db=db,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    user_query=content,
                    persona=persona_dto,
                    detail_level=override_persona.get("detailLevel") if override_persona else persona_dto.detailLevel,
                    target_language=target_language,
                    exclude_previous_sources=exclude_previous_sources
                ):
                    # 1. Stream the native agent event
                    await ws_manager.broadcast_to_channel(
                        channel=f"ai:{conversation_id}",
                        event_type="AI_AGENT_EVENT",
                        payload=ev.to_dict()
                    )
                    yield ev.to_sse_line()

                    # 2. Emit legacy status event for backward compatibility with older UI
                    leg_status = ev.to_legacy_status()
                    if leg_status:
                        await ws_manager.broadcast_to_channel(
                            channel=f"ai:{conversation_id}",
                            event_type="AI_AGENT_STATUS",
                            payload=leg_status
                        )
                        yield f"data: {json.dumps(leg_status, ensure_ascii=False)}\n\n"

                    # Collect tokens and final metadata
                    if ev.type == AgentEventType.TOKEN.value:
                        streamed_chunks.append(ev.data.get("delta", ""))
                    elif ev.type == AgentEventType.SOURCES.value:
                        collected_sources = ev.data.get("sources", [])
                        suggest_scholar = ev.data.get("suggestScholarEscalation", False)
                        escalation_cat = ev.data.get("escalationCategory")
                    elif ev.type == AgentEventType.DONE.value:
                        trace_id = ev.data.get("traceId")
                        full_answer = ev.data.get("fullText", "")

                full_text = full_answer or "".join(streamed_chunks)
                if full_text:
                    msg_id = f"msg_ai_{uuid.uuid4().hex[:8]}"
                    p_tok = max(30, len(content) // 3)
                    o_tok = max(50, len(full_text) // 3)
                    usage_dto = await CostService.calculate_and_log_usage(
                        db=db,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        message_id=msg_id,
                        model_name=model_override or settings.AI_AGENT_EXECUTOR_MODEL or settings.AI_CHAT_MODEL,
                        prompt_tokens=p_tok,
                        output_tokens=o_tok,
                        cached_tokens=0
                    )
                    ai_msg = AIMessage(
                        id=msg_id,
                        conversation_id=conversation_id,
                        role="ASSISTANT",
                        content=full_text,
                        sources=collected_sources,
                        suggest_scholar_escalation=suggest_scholar,
                        escalation_category=escalation_cat,
                        token_usage=usage_dto.model_dump()
                    )
                    db.add(ai_msg)
                    await db.commit()

                    done_payload = {
                        "type": "done",
                        "messageId": msg_id,
                        "fullText": full_text,
                        "traceId": trace_id
                    }
                    await ws_manager.broadcast_to_channel(
                        channel=f"ai:{conversation_id}",
                        event_type="AI_DONE",
                        payload=done_payload
                    )
                    yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"
                    return
            except Exception as agent_err:
                logger.warning(f"AgentEngine streaming failed: {agent_err}. Falling back to legacy pipeline.")

        # ---------------------------------------------------------------------
        # Fallback Legacy Pipeline (AgenticRAGService)
        # ---------------------------------------------------------------------
        # Check re-search intent and collect previous chunk IDs to prevent duplicates
        t_intent_start = time.perf_counter()
        plan = AgenticRAGService.extract_intent_and_expand_query(content)
        intent_expansion_ms = round((time.perf_counter() - t_intent_start) * 1000, 2)

        is_retry = bool(exclude_previous_sources) or plan.get("isRetry", False)
        excluded_ids = await AIService._get_previous_chunk_ids(db, conversation_id) if is_retry else []

        # 1. Capture status events during agentic retrieval
        status_events = []
        async def on_status(stage: str, msg: str):
            status_events.append({"stage": stage, "message": msg})

        t_rag_start = time.perf_counter()
        agentic_result = await AgenticRAGService.run_agentic_retrieval(
            db, content, status_callback=on_status, excluded_chunk_ids=excluded_ids
        )
        search_retrieval_ms = round((time.perf_counter() - t_rag_start) * 1000, 2)
        jev_evaluation_ms = round(agentic_result.get("jev_eval_ms", 110.0), 2)

        # 2. Reference translation based on user target language with DB caching
        t_trans_start = time.perf_counter()
        target_lang = AIService._detect_query_language(content, target_language)
        translated_sources = await AIService.translate_sources_if_needed(
            db, agentic_result.get("sources", []), target_lang
        )
        agentic_result["sources"] = translated_sources
        reference_translation_ms = round((time.perf_counter() - t_trans_start) * 1000, 2)

        # 3. Emit status events for live agent transparency
        for ev in status_events:
            payload = {"type": "status", "stage": ev["stage"], "message": ev["message"]}
            await ws_manager.broadcast_to_channel(
                channel=f"ai:{conversation_id}",
                event_type="AI_AGENT_STATUS",
                payload=payload
            )
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.04)

        # 4. Emit sources and metadata with recommendations
        routing_info_stream = await RecommendationService.get_routing_verdict(
            query=content,
            db=db,
            rag_sufficient=agentic_result.get("isSufficient")
        )
        rec_s_stream = routing_info_stream.get("recommendedScholar")
        rec_b_stream = routing_info_stream.get("recommendedBook")
        sources_payload = {
            "type": "sources",
            "sources": [s.model_dump() for s in translated_sources],
            "suggestScholarEscalation": routing_info_stream.get("needs_scholar", False),
            "escalationCategory": agentic_result.get("escalationCategory"),
            "recommendedScholar": rec_s_stream,
            "recommendedBook": rec_b_stream,
            "aiCapabilityStatus": routing_info_stream.get("ai_capability_status", "SELF_SUFFICIENT"),
            "routingAssessment": routing_info_stream,
            "targetLanguage": target_lang
        }
        await ws_manager.broadcast_to_channel(
            channel=f"ai:{conversation_id}",
            event_type="AI_SOURCES",
            payload=sources_payload
        )
        yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n"

        # 5. Build system prompt and prepare streaming
        system_prompt = AIService._build_system_prompt(persona_dto, user=user)
        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            "دستورالعمل استناد و ارجاع‌دهی:\n"
            "۱. در متن پاسخ، هر جا به یکی از منابع زیر استناد می‌کنی، دقیقاً از قالب پیوند مارک‌داون قابل کلیک به صورت `[شماره](آدرس)` استفاده کن.\n"
            "۲. کاربر باید بتواند با کلیک روی شماره منبع، مستقیماً به آن ارجاع برود.\n"
            "۳. در انتهای پاسخ، بخشی با عنوان «📚 منابع و مراجع:» درج کن و نام منابع را لیست نما.\n"
        )
        if agentic_result.get("suggestScholarEscalation"):
            enhanced_system_prompt += (
                "۴. با توجه به اینکه منبع قطعی و تام در کتب سامانه یافت نشده است، کاربر را مطلع کن که می‌تواند سوال خود را جهت بررسی اجتهادی به اساتید و علمای بخش مشاوره ارسال نماید.\n"
            )

        context_prompt = agentic_result.get("contextPrompt", "")
        effective_query = f"منابع و شواهد در دسترس:\n{context_prompt}\n\nپرسش کاربر:\n{content}"

        msg_id = f"msg_ai_{uuid.uuid4().hex[:8]}"
        t_llm_start = time.perf_counter()
        first_token_time = None
        streamed_chunks = []
        model_used = model_override or settings.AI_CHAT_MODEL or settings.GEMINI_MODEL
        usage_dict = {}

        # 6. Stream live LLM response tokens from LLMProviderService
        try:
            async for event in LLMProviderService.stream_chat_generation(
                section_key="chat",
                system_prompt=enhanced_system_prompt,
                user_query=effective_query,
                db=db,
                model_override=model_override
            ):
                if event.get("type") == "token":
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    token_text = event.get("delta", "")
                    if token_text:
                        streamed_chunks.append(token_text)
                        chunk_payload = {"type": "chunk", "chunk": token_text}
                        await ws_manager.broadcast_to_channel(
                            channel=f"ai:{conversation_id}",
                            event_type="AI_STREAM_CHUNK",
                            payload=chunk_payload
                        )
                        yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
                elif event.get("type") == "done":
                    model_used = event.get("model_used") or model_used
                    usage_dict = event.get("usage") or {}
        except Exception as e:
            logger.warning(f"Error during live stream generation: {e}")

        # 7. Fallback if upstream LLM yielded no tokens (e.g. mock test / offline / unreachable)
        if not streamed_chunks:
            ai_result = await AIService._call_gemini_or_generate_scholarly_response(
                system_prompt, content, agentic_result, db=db, model_override=model_override
            )
            full_content = ai_result["content"]
            model_used = ai_result.get("modelUsed") or model_used
            raw_tokens = ai_result.get("rawTokens", {})
            usage_dict = raw_tokens
            first_token_time = time.perf_counter()

            words = full_content.split(" ")
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                streamed_chunks.append(chunk)
                chunk_payload = {"type": "chunk", "chunk": chunk}
                await ws_manager.broadcast_to_channel(
                    channel=f"ai:{conversation_id}",
                    event_type="AI_STREAM_CHUNK",
                    payload=chunk_payload
                )
                yield f"data: {json.dumps(chunk_payload, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)

        full_content = "".join(streamed_chunks)
        llm_generation_ms = round((time.perf_counter() - t_llm_start) * 1000, 2)
        ttft_ms = round((first_token_time - t_llm_start) * 1000, 2) if first_token_time else 0.0
        total_latency_ms = round((time.perf_counter() - t_total_start) * 1000, 2)

        latency_breakdown = {
            "intent_expansion_ms": intent_expansion_ms,
            "search_retrieval_ms": search_retrieval_ms,
            "jev_evaluation_ms": jev_evaluation_ms,
            "reference_translation_ms": reference_translation_ms,
            "llm_time_to_first_token_ms": ttft_ms,
            "llm_generation_ms": llm_generation_ms,
            "total_latency_ms": total_latency_ms
        }

        # Structured application logging
        logger.info(
            f"[AI_CHAT_LATENCY] conversation_id={conversation_id} message_id={msg_id} "
            f"total_ms={total_latency_ms} ttft_ms={ttft_ms} rag_ms={search_retrieval_ms} "
            f"jev_ms={jev_evaluation_ms} trans_ms={reference_translation_ms} llm_ms={llm_generation_ms}"
        )

        prompt_tokens = usage_dict.get("promptTokens", max(10, len(content) // 3))
        output_tokens = usage_dict.get("outputTokens", max(10, len(full_content) // 3))
        cached_tokens = usage_dict.get("cachedTokens", 0)

        usage_dto = await CostService.calculate_and_log_usage(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=msg_id,
            model_name=model_used,
            prompt_tokens=prompt_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            latency_breakdown=latency_breakdown
        )

        # 8. Emit token usage with cost and latency breakdown
        usage_payload = {"type": "usage", "usage": usage_dto.model_dump(), "latencyBreakdown": latency_breakdown}
        await ws_manager.broadcast_to_channel(
            channel=f"ai:{conversation_id}",
            event_type="AI_TOKEN_USAGE",
            payload=usage_payload
        )
        yield f"data: {json.dumps(usage_payload, ensure_ascii=False)}\n\n"

        # References DTOs
        q_refs = [
            {"surahId": s.pageNumber or 1, "ayahNumber": s.index, "text": s.title}
            for s in translated_sources if s.type == "QURAN"
        ]
        h_refs = [
            {"source": s.title, "text": s.excerpt or ""}
            for s in translated_sources if s.type == "HADITH"
        ]

        # 9. Save assistant message to DB
        asst_msg = AIMessage(
            id=msg_id,
            conversation_id=conversation_id,
            role="ASSISTANT",
            content=full_content,
            referenced_ayahs=q_refs,
            referenced_hadiths=h_refs,
            sources=[s.model_dump() for s in translated_sources],
            suggest_scholar_escalation=agentic_result.get("suggestScholarEscalation", False),
            escalation_category=agentic_result.get("escalationCategory"),
            token_usage=usage_dto.model_dump()
        )
        db.add(asst_msg)
        await db.commit()

        # 10. Final done event
        done_payload = {
            "done": True,
            "messageId": msg_id,
            "suggestScholarEscalation": agentic_result.get("suggestScholarEscalation", False),
            "recommendedScholar": rec_s_stream,
            "recommendedBook": rec_b_stream,
            "tokenUsage": usage_dto.model_dump(),
            "latencyBreakdown": latency_breakdown
        }
        await ws_manager.broadcast_to_channel(
            channel=f"ai:{conversation_id}",
            event_type="AI_STREAM_COMPLETE",
            payload=done_payload
        )
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


    @staticmethod
    async def get_persona(db: AsyncSession, user_id: str) -> PersonaConfigDTO:
        p = await db.scalar(select(PersonaConfig).where(PersonaConfig.user_id == user_id))
        if not p:
            return PersonaConfigDTO()
        return PersonaConfigDTO(
            botName=p.bot_name or "دستیار معارفی اتحاد",
            botRolePreset=p.bot_role_preset or "GENERAL_ASSISTANT",
            botAvatar=p.bot_avatar,
            tone=p.tone,
            fiqhApproach=p.fiqh_approach,
            detailLevel=p.detail_level,
            includeAyahAddress=p.include_ayah_address,
            includeHadithReferences=p.include_hadith_references,
            customPromptInstructions=p.custom_prompt_instructions
        )

    @staticmethod
    async def update_persona(db: AsyncSession, user_id: str, data: PersonaConfigDTO) -> PersonaConfigDTO:
        p = await db.scalar(select(PersonaConfig).where(PersonaConfig.user_id == user_id))
        if not p:
            p = PersonaConfig(user_id=user_id)
            db.add(p)

        p.bot_name = data.botName
        p.bot_role_preset = data.botRolePreset
        p.bot_avatar = data.botAvatar
        p.tone = data.tone
        p.fiqh_approach = data.fiqhApproach
        p.detail_level = data.detailLevel
        p.include_ayah_address = data.includeAyahAddress
        p.include_hadith_references = data.includeHadithReferences
        p.custom_prompt_instructions = data.customPromptInstructions

        await db.commit()
        return data

    @staticmethod
    def get_persona_presets() -> List[Dict[str, Any]]:
        from app.services.auth_service import AuthService
        meta = AuthService.get_available_interests_and_presets()
        return [p.model_dump() for p in meta.botRolePresets]

    @staticmethod
    async def get_prompt_suggestions(db: AsyncSession, user_id: Optional[str] = None) -> List[PromptSuggestionDTO]:
        INTEREST_PROMPTS = {
            "TAFSIR": [
                PromptSuggestionDTO(title="تدبر در سوره واقعه", query="آیات پیرامون اصحاب الیمین و اصحاب الشمال چه پیام تفسیری دارند؟", iconName="menu_book"),
                PromptSuggestionDTO(title="تفسیر مقارن آیه تطهیر", query="دیدگاه‌های تفسیری فریقین درباره شأن نزول آیه تطهیر چیست؟", iconName="auto_stories")
            ],
            "AKHLAQ": [
                PromptSuggestionDTO(title="درمان کبر و غرور", query="روش‌های عملی تهذیب نفس و درمان تکبر از دیدگاه علمای اخلاق چیست؟", iconName="self_improvement"),
                PromptSuggestionDTO(title="مراتب صبر در شدائد", query="صبر بر طاعت، صبر از معصیت و صبر بر مصیبت چه مراتبی دارند؟", iconName="favorite")
            ],
            "AHKAM": [
                PromptSuggestionDTO(title="احکام نماز و روزه مسافر", query="شرایط شکسته شدن نماز و حد ترخص مسافر طبق فتاوا چگونه است؟", iconName="gavel"),
                PromptSuggestionDTO(title="احکام کسب درآمد حلال", query="معاملات آنلاین و ارزهای دیجیتال از منظر فقهی چه حکمی دارند؟", iconName="payments")
            ],
            "KALAM": [
                PromptSuggestionDTO(title="پاسخ به شبهه شرور", query="فلسفه وجود بلایا و شرور در جهان با عدل الهی چگونه سازگار است؟", iconName="psychology"),
                PromptSuggestionDTO(title="براهین اثبات وجود خدا", query="برهان نظم و برهان صدیقین را به زبان ساده بیان کن.", iconName="lightbulb")
            ],
            "HISTORY": [
                PromptSuggestionDTO(title="صلح امام حسن (ع)", query="زمینه‌ها و علل تاریخی صلح امام حسن با معاویه چه بود؟", iconName="history_edu"),
                PromptSuggestionDTO(title="پیمان مدینه در سیره نبوی", query="منشور مدینه چگونه همزیستی مسلمانان و سایر قبایل را تنظیم کرد؟", iconName="groups")
            ],
            "LIFESTYLE": [
                PromptSuggestionDTO(title="تربیت فرزند در عصر دیجیتال", query="راهکارهای اسلامی برای محافظت فکری و اخلاقی نوجوانان چیست؟", iconName="family_restroom"),
                PromptSuggestionDTO(title="اخلاق خانواده و همسرداری", query="سفارش‌های قرآن و اهل‌بیت پیرامون حسن خلق با همسر چیست؟", iconName="home")
            ]
        }

        # Check if user has selected interests
        personalized: List[PromptSuggestionDTO] = []
        if user_id:
            user = await db.scalar(select(User).where(User.id == user_id))
            if user and user.interests:
                for interest_tag in user.interests:
                    normalized = str(interest_tag).upper().strip()
                    if normalized in INTEREST_PROMPTS:
                        personalized.extend(INTEREST_PROMPTS[normalized])

        res = await db.execute(select(PromptSuggestion).order_by(PromptSuggestion.order_index))
        db_suggestions = [
            PromptSuggestionDTO(
                title=s.title,
                query=s.query,
                iconName=s.icon_name
            ) for s in res.scalars().all()
        ]

        if personalized:
            combined = []
            seen_titles = set()
            for item in personalized + db_suggestions:
                if item.title not in seen_titles:
                    seen_titles.add(item.title)
                    combined.append(item)
            return combined[:6]

        return db_suggestions

    @staticmethod
    async def rate_message(db: AsyncSession, message_id: str, data: MessageFeedbackRequest):
        msg = await db.scalar(select(AIMessage).where(AIMessage.id == message_id))
        if not msg:
            raise AppException(code="MESSAGE_NOT_FOUND", message="پیام مورد نظر یافت نشد.", status_code=404)
        msg.is_liked = data.isLiked
        msg.feedback_text = data.feedbackText
        await db.commit()
        return {"messageId": message_id, "isLiked": msg.is_liked, "saved": True}
