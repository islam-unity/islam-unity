import re
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc

from app.db.base import utc_now
from app.db.models import AIMessage, UserMemory, AIConversation
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)

# Topics and categories that MUST NEVER be persisted into long-term memory
SENSITIVE_PATTERNS = [
    r"طلاق", r"همسر", r"خیانت", r"گناه", r"توبه", r"اعتراف", r"بیماری", r"پزشک",
    r"قرض", r"بدهی", r"دعوا", r"خانوادگی", r"مشکل جنسی", r"راز", r"شرم", r"روانپزشک"
]


class MemoryService:
    """
    Manages short-term conversation context and privacy-preserving long-term user memories.
    """

    # -------------------------------------------------------------------------
    # 1. Short-Term Conversation Memory
    # -------------------------------------------------------------------------
    @classmethod
    async def get_conversation_history(
        cls,
        db: AsyncSession,
        conversation_id: str,
        limit_recent: int = 6
    ) -> List[Dict[str, str]]:
        """
        Retrieves the last N messages from the conversation for LLM context.
        """
        stmt = (
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(desc(AIMessage.created_at))
            .limit(limit_recent + 1)
        )
        res = await db.execute(stmt)
        messages = list(reversed(res.scalars().all()))

        history = []
        for msg in messages:
            role = "user" if msg.role == "USER" else "assistant"
            history.append({
                "role": role,
                "content": msg.content
            })
        return history

    @classmethod
    async def get_previous_source_ids(
        cls,
        db: AsyncSession,
        conversation_id: str
    ) -> List[str]:
        """
        Collects previously cited chunk/source IDs to prevent repetitive retrieval in follow-up queries.
        """
        stmt = (
            select(AIMessage.sources)
            .where(
                AIMessage.conversation_id == conversation_id,
                AIMessage.role == "ASSISTANT",
                AIMessage.sources.isnot(None)
            )
            .order_by(desc(AIMessage.created_at))
            .limit(10)
        )
        res = await db.execute(stmt)
        rows = res.scalars().all()

        chunk_ids = []
        for sources_list in rows:
            if isinstance(sources_list, list):
                for s in sources_list:
                    if isinstance(s, dict):
                        cid = s.get("id") or s.get("targetUrl")
                        if cid and cid not in chunk_ids:
                            chunk_ids.append(cid)
        return chunk_ids

    # -------------------------------------------------------------------------
    # 2. Long-Term Privacy-Preserving Memory
    # -------------------------------------------------------------------------
    @classmethod
    async def get_user_memory_context(
        cls,
        db: AsyncSession,
        user_id: Optional[str]
    ) -> str:
        """
        Builds a compact summary of user background memories for prompt injection.
        """
        if not user_id:
            return ""

        stmt = select(UserMemory).where(UserMemory.user_id == user_id)
        res = await db.execute(stmt)
        memories = res.scalars().all()

        if not memories:
            return ""

        lines = ["اطلاعات و ترجیحات فقهی/معارفی به خاطر سپرده شده کاربر:"]
        for m in memories:
            lines.append(f"- {m.key}: {m.value}")

        return "\n".join(lines)

    @classmethod
    async def list_user_memories(
        cls,
        db: AsyncSession,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Returns all long-term memories stored for a user.
        """
        stmt = select(UserMemory).where(UserMemory.user_id == user_id).order_by(desc(UserMemory.updated_at))
        res = await db.execute(stmt)
        memories = res.scalars().all()
        return [
            {
                "id": m.id,
                "category": m.category,
                "key": m.key,
                "value": m.value,
                "confidence": m.confidence,
                "updatedAt": m.updated_at.isoformat() if m.updated_at else None
            }
            for m in memories
        ]

    @classmethod
    async def delete_memory(
        cls,
        db: AsyncSession,
        user_id: str,
        memory_id: Optional[str] = None
    ) -> int:
        """
        Deletes a specific memory or clears all memories for a user.
        """
        if memory_id:
            stmt = delete(UserMemory).where(UserMemory.user_id == user_id, UserMemory.id == memory_id)
        else:
            stmt = delete(UserMemory).where(UserMemory.user_id == user_id)

        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount

    delete_user_memory = delete_memory

    @classmethod
    def _is_sensitive_text(cls, text: str) -> bool:
        """
        Guards against saving private, intimate, or sensitive disclosures.
        """
        for pat in SENSITIVE_PATTERNS:
            if re.search(pat, text):
                return True
        return False

    @classmethod
    async def extract_and_persist_memory(
        cls,
        db: AsyncSession,
        user_id: str,
        conversation_id: str,
        user_message: str,
        assistant_reply: str
    ):
        """
        Background task extracting non-sensitive preferences and background cues
        (Madhhab, preferred language, knowledge level, topics of interest, unresolved queries).
        Strictly filters out private or sensitive items.
        """
        if not user_id or len(user_message.strip()) < 10:
            return

        # Skip if sensitive keywords detected
        if cls._is_sensitive_text(user_message):
            logger.info("Memory extraction skipped: sensitive keywords detected in user message.")
            return

        extraction_prompt = (
            "وظیفه: تحلیل پیام کاربر و استخراج ترجیحات معارفی/فقهی پایدار جهت شخصی‌سازی در آینده.\n"
            "دسته‌بندی‌های مجاز:\n"
            "1. MADHHAB: مذهب فقهی صریح کاربر (مثلاً شافعی، حنفی، شیعه)\n"
            "2. LANGUAGE: زبان ترجیحی\n"
            "3. KNOWLEDGE_LEVEL: سطح دانش دینی (GENERAL, INTERMEDIATE, SCHOLAR)\n"
            "4. INTEREST: موضوعات مورد علاقه معارفی (مانند تفسیر، اخلاق، تاریخ، فقه معاملات)\n"
            "5. UNRESOLVED_QUESTION: سوال بی‌پاسخی که نیاز به پیگیری دارد\n\n"
            "قانون بحرانی عدم ثبت اطلاعات خصوصی:\n"
            "هرگز اطلاعات شخصی، خانوادگی، پزشکی، گناهان، اعترافات، اختلافات مالی یا روابط خصوصی را استخراج نکن.\n"
            "اگر نکته پایداری وجود ندارد، یک لیست خالی [] برگردان.\n\n"
            "فرمت خروجی صرفاً یک JSON Array معتبر:\n"
            '[{"category": "MADHHAB", "key": "مذهب کاربر", "value": "شافعی"}]\n\n'
            f"متن پیام کاربر:\n{user_message}"
        )

        try:
            items = []
            try:
                resp = await LLMProviderService.call_chat(
                    prompt=extraction_prompt,
                    section_key="agent_memory",
                    db=db,
                    temperature=0.1,
                    max_tokens=2500,
                    response_format={"type": "json_object"}
                )
                text = ""
                if isinstance(resp, dict):
                    text = str(resp.get("text") or "").strip()
                elif isinstance(resp, str):
                    text = resp.strip()

                if text:
                    if "<think>" in text:
                        if "</think>" in text:
                            text = text.split("</think>")[-1].strip()
                        else:
                            text = text.split("<think>")[-1].strip()

                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0].strip()
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0].strip()

                    parsed = None
                    try:
                        parsed = json.loads(text)
                    except Exception:
                        m = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", text)
                        if m:
                            try:
                                parsed = json.loads(m.group(1))
                            except Exception:
                                pass

                    if isinstance(parsed, list):
                        items = parsed
                    elif isinstance(parsed, dict) and "memories" in parsed and isinstance(parsed["memories"], list):
                        items = parsed["memories"]
            except Exception as e:
                logger.debug(f"LLM memory extraction failed: {e}")

            # Heuristic fallback if LLM is unavailable or offline
            if not items:
                q_lower = user_message.lower()
                if "شافع" in q_lower:
                    items.append({"category": "MADHHAB", "key": "مذهب فقهی", "value": "شافعی"})
                elif "حنف" in q_lower:
                    items.append({"category": "MADHHAB", "key": "مذهب فقهی", "value": "حنفی"})
                elif "جعفر" in q_lower or "شیع" in q_lower:
                    items.append({"category": "MADHHAB", "key": "مذهب فقهی", "value": "جعفری"})
                elif "مالک" in q_lower:
                    items.append({"category": "MADHHAB", "key": "مذهب فقهی", "value": "مالکی"})
                elif "حنبل" in q_lower:
                    items.append({"category": "MADHHAB", "key": "مذهب فقهی", "value": "حنبلی"})

            for item in items:
                category = item.get("category")
                key = item.get("key")
                value = item.get("value")

                if not category or not key or not value:
                    continue
                if category not in ("MADHHAB", "LANGUAGE", "KNOWLEDGE_LEVEL", "INTEREST", "UNRESOLVED_QUESTION"):
                    continue
                if cls._is_sensitive_text(str(value)) or cls._is_sensitive_text(str(key)):
                    continue

                # Check if memory already exists
                existing = await db.scalar(
                    select(UserMemory).where(
                        UserMemory.user_id == user_id,
                        UserMemory.category == category,
                        UserMemory.key == key
                    )
                )
                if existing:
                    existing.value = str(value)
                    existing.updated_at = utc_now()
                else:
                    new_mem = UserMemory(
                        id=f"mem_{uuid.uuid4().hex[:10]}",
                        user_id=user_id,
                        category=category,
                        key=key,
                        value=str(value),
                        confidence=0.9,
                        source_conversation_id=conversation_id
                    )
                    db.add(new_mem)

            await db.commit()
        except Exception as e:
            logger.debug(f"Memory extraction non-blocking error: {e}")
