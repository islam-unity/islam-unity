import time
import uuid
import secrets
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.base import utc_now
from app.db.models import (
    DeveloperAccount, DeveloperApiKey, User, Book, BookChapter, KnowledgeChunk
)
from app.schemas.developer import (
    DeveloperAccountDTO, ApiKeyDTO, ApiKeyCreatedResponse, DeveloperUsageDTO,
    OpenAIChatCompletionRequest, OpenAIChatCompletionResponse, OpenAIChatChoice,
    OpenAIChatChoiceMessage, OpenAIUsage, DeveloperAskRequest, DeveloperAskResponse,
    DeveloperRAGSearchRequest, DeveloperRAGSearchResultItem,
    DeveloperLibrarySearchRequest, DeveloperBookChatRequest
)
from app.core.exceptions import (
    ApiKeyInvalidException, DeveloperQuotaExceededException, DeveloperRateLimitException,
    BookNotFoundException, AppException
)
from app.services.agentic_rag_service import AgenticRAGService
from app.services.cost_service import CostService
from app.services.llm_provider_service import LLMProviderService
from app.services.library_service import LibraryService
from app.services.vector_service import VectorService

logger = logging.getLogger(__name__)

# In-memory sliding window for rate limiting: key_id -> list of float timestamps
_RATE_LIMIT_STORE: Dict[str, List[float]] = {}


class DeveloperService:

    # =========================================================================
    # 1. API Key & Account Management
    # =========================================================================

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()

    @classmethod
    async def get_or_create_account(
        cls, db: AsyncSession, user_id: str, app_name: str = "پروژه معارفی من", description: Optional[str] = None
    ) -> DeveloperAccount:
        account = await db.scalar(
            select(DeveloperAccount).options(selectinload(DeveloperAccount.api_keys)).where(DeveloperAccount.user_id == user_id)
        )
        if not account:
            account = DeveloperAccount(
                id=f"dev_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                app_name=app_name,
                description=description,
                tier="STANDARD",
                monthly_quota_tokens=5_000_000,
                used_tokens_this_month=0,
                rate_limit_per_minute=60,
                quota_reset_at=utc_now(),
                is_active=True,
                created_at=utc_now()
            )
            db.add(account)
            await db.commit()
            await db.refresh(account)
        return account

    @classmethod
    async def create_api_key(
        cls, db: AsyncSession, account_id: str, label: str = "کلید اصلی"
    ) -> ApiKeyCreatedResponse:
        account = await db.scalar(select(DeveloperAccount).where(DeveloperAccount.id == account_id))
        if not account:
            raise AppException(code="ACCOUNT_NOT_FOUND", message="حساب کاربری توسعه‌دهنده یافت نشد.", status_code=404)

        # Generate cryptographic raw key: ak_live_ + 48 hex chars
        random_token = secrets.token_hex(24)
        raw_key = f"ak_live_{random_token}"
        key_prefix = raw_key[:12] + "..."
        hashed = cls.hash_key(raw_key)

        key_id = f"key_{uuid.uuid4().hex[:12]}"
        now = utc_now()
        api_key = DeveloperApiKey(
            id=key_id,
            account_id=account_id,
            key_prefix=key_prefix,
            key_hash=hashed,
            label=label or "کلید اصلی",
            is_active=True,
            total_requests=0,
            total_tokens=0,
            created_at=now
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        return ApiKeyCreatedResponse(
            id=api_key.id,
            label=api_key.label,
            key=raw_key,
            keyPrefix=api_key.key_prefix,
            createdAt=api_key.created_at.isoformat()
        )

    @classmethod
    async def list_api_keys(cls, db: AsyncSession, account_id: str) -> List[ApiKeyDTO]:
        res = await db.execute(
            select(DeveloperApiKey).where(DeveloperApiKey.account_id == account_id).order_by(desc(DeveloperApiKey.created_at))
        )
        keys = res.scalars().all()
        return [
            ApiKeyDTO(
                id=k.id,
                label=k.label,
                keyPrefix=k.key_prefix,
                totalRequests=k.total_requests,
                totalTokens=k.total_tokens,
                lastUsedAt=k.last_used_at.isoformat() if k.last_used_at else None,
                isActive=k.is_active,
                createdAt=k.created_at.isoformat()
            ) for k in keys
        ]

    @classmethod
    async def revoke_api_key(cls, db: AsyncSession, account_id: str, key_id: str) -> bool:
        key = await db.scalar(
            select(DeveloperApiKey).where(
                DeveloperApiKey.id == key_id,
                DeveloperApiKey.account_id == account_id
            )
        )
        if not key:
            raise AppException(code="KEY_NOT_FOUND", message="کلید API مورد نظر یافت نشد.", status_code=404)
        
        key.is_active = False
        await db.commit()
        return True

    @classmethod
    async def get_usage_overview(cls, db: AsyncSession, account_id: str) -> DeveloperUsageDTO:
        account = await db.scalar(
            select(DeveloperAccount).options(selectinload(DeveloperAccount.api_keys)).where(DeveloperAccount.id == account_id)
        )
        if not account:
            raise AppException(code="ACCOUNT_NOT_FOUND", message="حساب کاربری توسعه‌دهنده یافت نشد.", status_code=404)

        total_requests = sum(k.total_requests for k in account.api_keys)
        total_tokens = sum(k.total_tokens for k in account.api_keys)
        remaining = max(0, account.monthly_quota_tokens - account.used_tokens_this_month)

        currency_cfg = await CostService.get_or_init_currency_config(db)
        pricing = await CostService.get_or_init_model_pricing(db, settings.GEMINI_MODEL)
        
        est_cost_usd = (account.used_tokens_this_month / 1_000_000.0) * float(pricing.input_cost_per_million_usd)
        est_cost_irr = est_cost_usd * float(currency_cfg.usd_to_irr_rate)

        next_reset = (account.quota_reset_at + timedelta(days=30)).isoformat() if account.quota_reset_at else None

        return DeveloperUsageDTO(
            accountId=account.id,
            appName=account.app_name,
            tier=account.tier,
            totalRequests=total_requests,
            totalTokensUsed=total_tokens,
            monthlyQuota=account.monthly_quota_tokens,
            remainingQuota=remaining,
            estimatedCostUsd=round(est_cost_usd, 4),
            estimatedCostIrr=round(est_cost_irr, 0),
            resetDate=next_reset
        )

    # =========================================================================
    # 2. Authentication, Rate Limiting & Quota Validation
    # =========================================================================

    @classmethod
    async def authenticate_developer_request(
        cls, db: AsyncSession, api_key_raw: Optional[str]
    ) -> Tuple[DeveloperAccount, DeveloperApiKey]:
        if not api_key_raw or not api_key_raw.strip():
            raise ApiKeyInvalidException(message="هدر X-API-Key الزامی است.")

        raw_key = api_key_raw.strip()
        hashed = cls.hash_key(raw_key)

        stmt = select(DeveloperApiKey).options(
            selectinload(DeveloperApiKey.account)
        ).where(
            DeveloperApiKey.key_hash == hashed,
            DeveloperApiKey.is_active == True
        )
        key_record = await db.scalar(stmt)
        if not key_record or not key_record.account or not key_record.account.is_active:
            raise ApiKeyInvalidException(message="کلید API نامعتبر است یا حساب توسعه‌دهنده غیرفعال شده است.")

        account = key_record.account

        # 1. Quota reset check (every 30 days)
        now_dt = utc_now()
        if account.quota_reset_at:
            reset_dt = account.quota_reset_at.replace(tzinfo=None) if hasattr(account.quota_reset_at, 'tzinfo') and account.quota_reset_at.tzinfo else account.quota_reset_at
            if (now_dt - reset_dt).days >= 30:
                account.used_tokens_this_month = 0
                account.quota_reset_at = now_dt
                await db.commit()

        # 2. Quota exceeded check
        if account.used_tokens_this_month >= account.monthly_quota_tokens:
            raise DeveloperQuotaExceededException(
                f"سهمیه توکن ماهانه حساب توسعه‌دهنده به اتمام رسیده است ({account.used_tokens_this_month:,} / {account.monthly_quota_tokens:,})."
            )

        # 3. Sliding window Rate Limiter check (per minute)
        now_ts = time.time()
        timestamps = _RATE_LIMIT_STORE.get(key_record.id, [])
        # Keep only timestamps within the last 60 seconds
        timestamps = [t for t in timestamps if now_ts - t < 60.0]

        if len(timestamps) >= account.rate_limit_per_minute:
            _RATE_LIMIT_STORE[key_record.id] = timestamps
            raise DeveloperRateLimitException(
                f"نرخ فراخوانی بیش از سقف مجاز ({account.rate_limit_per_minute} درخواست در دقیقه) است."
            )

        timestamps.append(now_ts)
        _RATE_LIMIT_STORE[key_record.id] = timestamps

        # Update last used timestamp & request count
        key_record.last_used_at = now_dt
        key_record.total_requests += 1
        await db.commit()

        return account, key_record

    @classmethod
    async def record_token_usage(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        prompt_tokens: int,
        completion_tokens: int,
        model_name: str
    ) -> None:
        total = prompt_tokens + completion_tokens
        account.used_tokens_this_month += total
        key.total_tokens += total

        try:
            await CostService.calculate_and_log_usage(
                db=db,
                user_id=account.user_id,
                conversation_id=None,
                message_id=None,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cached_tokens=0
            )
        except Exception as e:
            logger.warning(f"Failed to log detailed cost for developer API: {e}")

        await db.commit()

    # =========================================================================
    # 3. AI Capabilities for Developers
    # =========================================================================

    @classmethod
    async def chat_completions(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        request: OpenAIChatCompletionRequest
    ) -> OpenAIChatCompletionResponse:
        # Extract last user message as query
        user_messages = [m.content for m in request.messages if m.role.lower() == "user"]
        system_messages = [m.content for m in request.messages if m.role.lower() == "system"]
        user_query = user_messages[-1] if user_messages else "سلام"
        system_context = "\n".join(system_messages) if system_messages else "شما یک دستیار هوشمند، امین و مستند به منابع معارفی و علوم اسلامی هستید."

        # Religious controls from extra_params if provided
        extra = request.extra_params or {}
        madhab = extra.get("madhab", "taqrib")
        tone = extra.get("tone", "general")

        madhab_guide = {
            "jafari": "مذهب فقهی: شیعه امامیه (جعفری)",
            "hanafi": "مذهب فقهی: اهل سنت (حنفی)",
            "shafii": "مذهب فقهی: اهل سنت (شافعی)",
            "maliki": "مذهب فقهی: اهل سنت (مالکی)",
            "hanbali": "مذهب فقهی: اهل سنت (حنبلی)",
            "taqrib": "رویکرد فقهی: تقریب مذاهب و بیان مشترکات اسلامی"
        }.get(madhab, "رویکرد فقهی: تقریب مذاهب اسلامی")

        enhanced_system = f"{system_context}\n\nرویکرد معارفی: {madhab_guide}\nلحن: {tone}\nپاسخ باید مستند، موثق، صریح و با ادب اسلامی ارائه شود."

        # Perform Agentic RAG
        rag_res = await AgenticRAGService.run_agentic_retrieval(db, user_query)
        sources = rag_res.get("sources", [])
        context_prompt = rag_res.get("contextPrompt", "")

        # Call configured LLM
        model_name = request.model or settings.AI_CHAT_MODEL or settings.GEMINI_MODEL
        llm_response = await LLMProviderService.call_chat_generation(
            section_key="chat",
            system_prompt=enhanced_system,
            user_query=f"منابع معارفی مستخرج:\n{context_prompt}\n\nپرسش:\n{user_query}",
            db=db,
            model_override=model_name
        )

        content = ""
        prompt_tokens = max(10, (len(user_query) + len(context_prompt)) // 3)
        completion_tokens = 50

        if llm_response and llm_response.get("text"):
            content = llm_response["text"]
            usage_dict = llm_response.get("usage", {})
            prompt_tokens = usage_dict.get("promptTokens", prompt_tokens)
            completion_tokens = usage_dict.get("outputTokens", max(10, len(content) // 3))
        else:
            # Fallback high quality response
            content = "بر اساس منابع اسلامی و کتب معتبر بررسی‌شده:\n"
            if sources:
                for s in sources[:3]:
                    snip = getattr(s, 'excerpt', None) or getattr(s, 'snippet', '') or ''
                    content += f"- **{s.title}**: {snip}\n"
            else:
                content += "موضوع مطروحه در مبانی فقه و معارف اسلامی نیازمند تطبیق دقیق با ادله و فتاوای معتبر است."

        # Record usage
        await cls.record_token_usage(
            db=db,
            account=account,
            key=key,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_name=model_name
        )

        citations_out = [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in sources]

        return OpenAIChatCompletionResponse(
            id=f"chatcmpl_{uuid.uuid4().hex[:12]}",
            object="chat.completion",
            created=int(time.time()),
            model=model_name,
            choices=[
                OpenAIChatChoice(
                    index=0,
                    message=OpenAIChatChoiceMessage(role="assistant", content=content),
                    finish_reason="stop"
                )
            ],
            citations=citations_out,
            usage=OpenAIUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )

    @classmethod
    async def stream_chat_completions(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        request: OpenAIChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        cmpl_id = f"chatcmpl_{uuid.uuid4().hex[:12]}"
        created = int(time.time())
        model_name = request.model or settings.AI_CHAT_MODEL or settings.GEMINI_MODEL

        # Get full result
        full_res = await cls.chat_completions(db, account, key, request)
        full_text = full_res.choices[0].message.content

        # Stream chunks
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk_content = word + (" " if i < len(words) - 1 else "")
            chunk_data = {
                "id": cmpl_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": chunk_content},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

        # Final chunk
        final_chunk = {
            "id": cmpl_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }
            ],
            "citations": full_res.citations
        }
        yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    @classmethod
    async def ask_religious(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        request: DeveloperAskRequest
    ) -> DeveloperAskResponse:
        openai_req = OpenAIChatCompletionRequest(
            messages=[{"role": "user", "content": request.query}],
            extra_params={
                "madhab": request.madhab,
                "tone": request.tone,
                "source_filter": request.source_filter
            }
        )
        cmpl = await cls.chat_completions(db, account, key, openai_req)
        answer_text = cmpl.choices[0].message.content
        citations = cmpl.citations or []

        q_refs = [
            {"surahId": c.get("pageNumber", 1), "ayahNumber": c.get("index", 1), "text": c.get("title", "")}
            for c in citations if c.get("type") == "QURAN"
        ]
        h_refs = [
            {"source": c.get("title", ""), "text": c.get("excerpt", "")}
            for c in citations if c.get("type") == "HADITH"
        ]

        return DeveloperAskResponse(
            answer=answer_text,
            citations=citations,
            suggestScholarEscalation=False,
            referencedAyahs=q_refs,
            referencedHadiths=h_refs,
            modelUsed=cmpl.model,
            usage=cmpl.usage
        )

    @classmethod
    async def rag_search(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        request: DeveloperRAGSearchRequest
    ) -> List[DeveloperRAGSearchResultItem]:
        # Perform vector search through VectorService
        raw_hits = await VectorService.search_semantic(
            query=request.query,
            limit=request.limit or 5
        )

        results: List[DeveloperRAGSearchResultItem] = []
        if raw_hits:
            for hit in raw_hits:
                score = hit.get("score", 0.8)
                if request.min_relevance_score and score < request.min_relevance_score:
                    continue
                results.append(
                    DeveloperRAGSearchResultItem(
                        chunkId=str(hit.get("chunkId") or uuid.uuid4().hex[:8]),
                        bookTitle=hit.get("bookTitle", "کتاب اسلامی"),
                        author=hit.get("author"),
                        chapterTitle=hit.get("chapterTitle"),
                        volume=hit.get("volume"),
                        page=hit.get("pageNumber"),
                        text=hit.get("text", ""),
                        score=score
                    )
                )

        # Fallback to SQL text search if vector db returned few results
        if len(results) < (request.limit or 5):
            needed = (request.limit or 5) - len(results)
            sql_chunks = await db.execute(
                select(KnowledgeChunk).options(
                    selectinload(KnowledgeChunk.book),
                    selectinload(KnowledgeChunk.chapter)
                ).where(
                    KnowledgeChunk.full_text.ilike(f"%{request.query}%")
                ).limit(needed)
            )
            for c in sql_chunks.scalars().all():
                book_title = c.book.title if c.book else "کتاب معارفی"
                author_name = c.book.author if c.book else None
                chapter_title = c.chapter.title if c.chapter else None
                vol = c.book.volume_count if c.book and hasattr(c.book, "volume_count") else None
                results.append(
                    DeveloperRAGSearchResultItem(
                        chunkId=c.id,
                        bookTitle=book_title,
                        author=author_name,
                        chapterTitle=chapter_title,
                        volume=vol,
                        page=c.page_number,
                        text=c.full_text[:400],
                        score=0.85
                    )
                )

        # Count 1 lightweight request token usage (10 tokens)
        await cls.record_token_usage(
            db=db,
            account=account,
            key=key,
            prompt_tokens=len(request.query) // 3 + 1,
            completion_tokens=len(results) * 15,
            model_name="qdrant-search"
        )

        return results

    # =========================================================================
    # 4. Library Capabilities for Developers
    # =========================================================================

    @classmethod
    async def get_books_catalog(
        cls,
        db: AsyncSession,
        category_id: Optional[str] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        return await LibraryService.get_books(
            db=db,
            category_id=category_id,
            q=q,
            page=page,
            limit=limit
        )

    @classmethod
    async def get_book_detail(cls, db: AsyncSession, book_id: str) -> Dict[str, Any]:
        book = await LibraryService.get_book_detail(db, book_id)
        return book.model_dump()

    @classmethod
    async def get_chapter_detail(cls, db: AsyncSession, book_id: str, chapter_id: str) -> Dict[str, Any]:
        chapter = await LibraryService.get_chapter_detail(db, book_id, chapter_id)
        return chapter.model_dump()

    @classmethod
    async def search_library(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        request: DeveloperLibrarySearchRequest
    ) -> Dict[str, Any]:
        limit = request.limit or 10

        # Vector / Semantic Search
        if request.search_mode in ["vector", "hybrid"]:
            semantic_results = await LibraryService.semantic_search(
                db=db,
                query=request.query,
                limit=limit,
                category_id=request.category_id
            )
            items = [s.model_dump() for s in semantic_results]
        else:
            # Pure text search
            books_res = await LibraryService.get_books(
                db=db,
                category_id=request.category_id,
                q=request.query,
                page=1,
                limit=limit
            )
            items = [b.model_dump() for b in books_res["items"]]

        # Lightweight usage deduction
        await cls.record_token_usage(
            db=db,
            account=account,
            key=key,
            prompt_tokens=len(request.query) // 3 + 1,
            completion_tokens=len(items) * 10,
            model_name="library-fast-search"
        )

        return {
            "query": request.query,
            "totalResults": len(items),
            "results": items
        }

    @classmethod
    async def chat_with_book(
        cls,
        db: AsyncSession,
        account: DeveloperAccount,
        key: DeveloperApiKey,
        book_id: str,
        request: DeveloperBookChatRequest
    ) -> Dict[str, Any]:
        res = await LibraryService.ai_chat_with_book(db, book_id, request.query)

        # Record usage
        await cls.record_token_usage(
            db=db,
            account=account,
            key=key,
            prompt_tokens=len(request.query) // 3 + 50,
            completion_tokens=len(res.answer) // 3,
            model_name="book-rag"
        )

        return res.model_dump()
