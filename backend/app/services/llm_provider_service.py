import os
import time
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, Tuple, AsyncGenerator
from datetime import datetime, timezone
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.base import utc_now
from app.db.models.ai_chat import AISectionConfig
from app.schemas.ai_chat import (
    SectionModelConfigDTO, UpdateSectionModelConfigRequest,
    BulkUpdateSectionModelConfigRequest, TestModelConnectionRequest,
    TestModelConnectionResponse
)

logger = logging.getLogger(__name__)


class ChatResponseStr(str):
    """
    A string subclass that allows .get("text") and ["text"] for backward compatibility
    with callers that expect either a dict with a 'text' key or a plain string.
    """
    def get(self, key: str, default: Any = None) -> Any:
        if key == "text":
            return str(self)
        return default

    def __getitem__(self, item: Any) -> Any:
        if item == "text":
            return str(self)
        return super().__getitem__(item)


class AsyncRateLimiter:
    """
    Sliding-window asynchronous rate limiter with burst smoothing.
    Enforces maximum requests within a time window (e.g., 40 RPM for Nvidia NIM) and
    smooths burst concurrency with minimum intervals.
    """
    def __init__(self, max_calls: int = 40, period_seconds: float = 60.0, min_interval: float = 1.0):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.min_interval = min_interval
        self._timestamps: List[float] = []
        self._lock = asyncio.Lock()
        self._last_call_time: float = 0.0

    async def acquire(self):
        async with self._lock:
            now = time.time()
            cutoff = now - self.period_seconds
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self.max_calls:
                oldest = self._timestamps[0]
                wait_time = (oldest + self.period_seconds) - now + 0.1
                if wait_time > 0:
                    logger.info(
                        f"NVIDIA Rate Limiter: Reached {self.max_calls} requests per {self.period_seconds}s limit. "
                        f"Throttling for {wait_time:.2f}s..."
                    )
                    await asyncio.sleep(wait_time)
                now = time.time()
                cutoff = now - self.period_seconds
                self._timestamps = [t for t in self._timestamps if t > cutoff]

            # Burst smoothing
            elapsed = now - self._last_call_time
            if elapsed < self.min_interval:
                smooth_wait = self.min_interval - elapsed
                await asyncio.sleep(smooth_wait)
                now = time.time()

            self._last_call_time = now
            self._timestamps.append(now)

    def record_429(self, backoff_seconds: float = 2.0):
        """Forces a temporary backoff when an external 429 response is observed."""
        now = time.time()
        self._last_call_time = max(self._last_call_time, now + backoff_seconds)


class LLMProviderService:
    """
    Centralized model & base_url dispatcher supporting:
    - Independent per-section model, base_url, api_key and provider configuration
    - Fallback to settings / environment variables
    - Support for Google Gemini native API and OpenAI-compatible endpoints (vLLM, Ollama, OpenRouter, etc.)
    - Safe key masking and dynamic runtime updates via database
    - Automatic sequential model fallback (Failover Chain) and 40 RPM rate limiting for Nvidia NIM
    """

    _rate_limiters: Dict[str, AsyncRateLimiter] = {}

    @classmethod
    def get_rate_limiter(cls, key: str, rpm_limit: int = 40) -> AsyncRateLimiter:
        if key not in cls._rate_limiters:
            min_interval = max(0.5, 60.0 / float(rpm_limit))
            cls._rate_limiters[key] = AsyncRateLimiter(
                max_calls=rpm_limit,
                period_seconds=60.0,
                min_interval=min_interval
            )
        return cls._rate_limiters[key]

    SECTIONS_METADATA: Dict[str, Dict[str, Any]] = {
        "chat": {
            "name_fa": "گفتگوی هوشمند معارفی (AI Chat)",
            "description_fa": "پاسخ به سوالات معارفی، احکام و استنادات قرآنی/روایی و استریم زنده پاسخ",
            "default_model": lambda: settings.AI_CHAT_MODEL or settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.AI_CHAT_BASE_URL or settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.AI_CHAT_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.AI_CHAT_PROVIDER or "gemini",
        },
        "embedding": {
            "name_fa": "تعبیه برداری و جستجوی معنایی (Vector Embeddings)",
            "description_fa": "تولید بردار ۷۶۸ بعدی جهت جستجوی معنایی و پایگاه داده کیودرانت (Qdrant)",
            "default_model": lambda: settings.AI_EMBEDDING_MODEL or settings.GEMINI_EMBEDDING_MODEL,
            "default_base_url": lambda: settings.AI_EMBEDDING_BASE_URL or settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.AI_EMBEDDING_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.AI_EMBEDDING_PROVIDER or "gemini",
        },
        "agentic_rag": {
            "name_fa": "موتور عامل هوشمند RAG (Agentic RAG Engine)",
            "description_fa": "تحلیل قصد کاربر، تجزیه کوئری به چند پرسش، برنامه‌ریزی جستجوی ترکیبی و بازنویسی کوئری",
            "default_model": lambda: settings.AI_AGENTIC_RAG_MODEL or settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.AI_AGENTIC_RAG_BASE_URL or settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.AI_AGENTIC_RAG_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.AI_AGENTIC_RAG_PROVIDER or "gemini",
        },
        "jev": {
            "name_fa": "موتور تصمیم‌گیری سامانه یک JEV (Decision Engine)",
            "description_fa": "تصمیم‌گیری سریع غیرتولیدی، انتخاب فصل کتاب و ارزیابی کالیبره‌شده کفایت شواهد",
            "default_model": lambda: settings.JEV_MODEL or "systemone-v1",
            "default_base_url": lambda: settings.JEV_BASE_URL or settings.JEV_API_URL,
            "default_api_key": lambda: settings.JEV_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.JEV_PROVIDER or "jev_systemone",
        },
        "library": {
            "name_fa": "هوش مصنوعی کتابخانه و کتب (Library AI)",
            "description_fa": "چت تخصصی با محتوای کتب اسلامی و تحلیل عمیق، خلاصه‌سازی و اصطلاح‌شناسی فصول",
            "default_model": lambda: settings.AI_LIBRARY_MODEL or settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.AI_LIBRARY_BASE_URL or settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.AI_LIBRARY_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.AI_LIBRARY_PROVIDER or "gemini",
        },
        "quran": {
            "name_fa": "تدبر و تحلیل هوشمند آیات (Quran Tadabbur AI)",
            "description_fa": "استخراج نکات تدبری، پیوندهای مفهومی و تحلیل ادبی آیات سوره",
            "default_model": lambda: settings.AI_QURAN_MODEL or settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.AI_QURAN_BASE_URL or settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.AI_QURAN_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.AI_QURAN_PROVIDER or "gemini",
        },
        "consultation": {
            "name_fa": "دستیار هوشمند مشاوران و علما (Consultation AI)",
            "description_fa": "تریاژ خودکار سوالات، پیشنهاد پیش‌نویس پاسخ برای اساتید و دسته‌بندی استفتائات",
            "default_model": lambda: settings.AI_CONSULTATION_MODEL or settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.AI_CONSULTATION_BASE_URL or settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.AI_CONSULTATION_API_KEY or settings.GEMINI_API_KEY,
            "default_provider": lambda: settings.AI_CONSULTATION_PROVIDER or "gemini",
        },
        "agent_planner": {
            "name_fa": "طراح استدلال و نقشه راه ایجنت (Agent Planner)",
            "description_fa": "استخراج اهداف، تحلیل پیش‌زمینه و پرسونا، تفکیک سوال به زیرمسائل و تدوین نقشه ساختاریافته",
            "default_model": lambda: settings.AI_AGENT_PLANNER_MODEL or "deepseek-flash",
            "default_base_url": lambda: settings.AI_AGENT_PLANNER_BASE_URL or "https://api.deepseek.com",
            "default_api_key": lambda: settings.AI_AGENT_PLANNER_API_KEY or settings.DEEPSEEK_API_KEY_UNITY,
            "default_provider": lambda: settings.AI_AGENT_PLANNER_PROVIDER or "openai_compatible",
        },
        "agent_executor": {
            "name_fa": "مجری چرخه ابزار و تحلیل شواهد (Agent ReAct Executor)",
            "description_fa": "فراخوانی ابزارهای تخصصی کتابخانه، قرآن و مقایسه مذاهب با تصمیم‌گیری ReAct",
            "default_model": lambda: settings.AI_AGENT_EXECUTOR_MODEL or "deepseek-flash",
            "default_base_url": lambda: settings.AI_AGENT_EXECUTOR_BASE_URL or "https://api.deepseek.com",
            "default_api_key": lambda: settings.AI_AGENT_EXECUTOR_API_KEY or settings.DEEPSEEK_API_KEY_UNITY,
            "default_provider": lambda: settings.AI_AGENT_EXECUTOR_PROVIDER or "openai_compatible",
        },
        "agent_verifier": {
            "name_fa": "ارزیاب و اعتبارسنج احکام و ارجاعات (Agent Verifier)",
            "description_fa": "بررسی تطابق فتواها و نظرات فقهی با متن مستندات و اصالت ارجاعات",
            "default_model": lambda: settings.AI_AGENT_VERIFIER_MODEL or "deepseek-flash",
            "default_base_url": lambda: settings.AI_AGENT_VERIFIER_BASE_URL or "https://api.deepseek.com",
            "default_api_key": lambda: settings.AI_AGENT_VERIFIER_API_KEY or settings.DEEPSEEK_API_KEY_UNITY,
            "default_provider": lambda: settings.AI_AGENT_VERIFIER_PROVIDER or "openai_compatible",
        },
        "agent_memory": {
            "name_fa": "استخراج‌گر و پالاینده حافظه بلندمدت (Agent Memory Extractor)",
            "description_fa": "استخراج امن ترجیحات فقهی، علایق و سوالات بی‌پاسخ بدون ذخیره اطلاعات حساس",
            "default_model": lambda: settings.AI_AGENT_MEMORY_MODEL or "deepseek-flash",
            "default_base_url": lambda: settings.AI_AGENT_MEMORY_BASE_URL or "https://api.deepseek.com",
            "default_api_key": lambda: settings.AI_AGENT_MEMORY_API_KEY or settings.DEEPSEEK_API_KEY_UNITY,
            "default_provider": lambda: settings.AI_AGENT_MEMORY_PROVIDER or "openai_compatible",
        },
        "chunk_representation": {
            "name_fa": "پردازش چانک‌ها و تولید نماینده‌ها (Chunk Representation AI)",
            "description_fa": "پردازش پس‌زمینه بدون وقفه، خلاصه‌سازی فشرده، تولید سوالات فرضی و استخراج مفاهیم با مدل‌های انویدیا (NVIDIA NIM)",
            "default_model": lambda: settings.AI_CHUNK_REPRESENTATION_MODEL or settings.NVIDIA_DEFAULT_MODEL,
            "default_base_url": lambda: settings.AI_CHUNK_REPRESENTATION_BASE_URL or settings.NVIDIA_BASE_URL,
            "default_api_key": lambda: settings.AI_CHUNK_REPRESENTATION_API_KEY or settings.NVIDIA_API_KEY,
            "default_provider": lambda: settings.AI_CHUNK_REPRESENTATION_PROVIDER or "openai_compatible",
        }
    }

    @staticmethod
    def mask_api_key(api_key: Optional[str]) -> Optional[str]:
        if not api_key or not api_key.strip():
            return None
        clean = api_key.strip()
        if len(clean) <= 8:
            return "***"
        return f"{clean[:4]}...{clean[-4:]}"

    @classmethod
    async def get_section_config(
        cls,
        db: Optional[AsyncSession],
        section_key: str
    ) -> Dict[str, Any]:
        """
        Retrieves section config: looks up DB first, falls back to settings/env.
        """
        meta = cls.SECTIONS_METADATA.get(section_key, {
            "name_fa": section_key,
            "description_fa": None,
            "default_model": lambda: settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.GEMINI_API_KEY,
            "default_provider": lambda: "gemini",
        })

        db_row: Optional[AISectionConfig] = None
        if db is not None:
            try:
                db_row = await db.scalar(
                    select(AISectionConfig).where(AISectionConfig.section_key == section_key)
                )
            except Exception as e:
                logger.warning(f"Could not load AISectionConfig for '{section_key}': {e}")

        # Check if the DB row has an explicitly customized API key
        has_custom_key = bool(db_row and db_row.api_key and db_row.api_key.strip())
        is_legacy_gemini = bool(db_row and not has_custom_key and "gemini" in (db_row.model_name or ""))

        # Model name
        model_name = (
            db_row.model_name if (db_row and db_row.model_name and not is_legacy_gemini)
            else meta["default_model"]()
        )

        # Base URL
        base_url = (
            db_row.base_url if (db_row and db_row.base_url and not is_legacy_gemini)
            else meta["default_base_url"]()
        )
        if not base_url:
            base_url = meta["default_base_url"]() or settings.GEMINI_BASE_URL

        # API Key
        api_key = (
            db_row.api_key if has_custom_key
            else meta["default_api_key"]()
        )
        if not api_key:
            api_key = settings.GEMINI_API_KEY

        # Provider
        provider = (
            db_row.provider if (db_row and db_row.provider and not is_legacy_gemini)
            else meta["default_provider"]()
        )

        # Is Active
        is_active = db_row.is_active if db_row is not None else True
        extra_params = db_row.extra_params if db_row and db_row.extra_params else {}
        updated_at = int(db_row.updated_at.timestamp() * 1000) if db_row and db_row.updated_at else None

        return {
            "section_key": section_key,
            "section_name_fa": db_row.section_name_fa if db_row else meta["name_fa"],
            "description_fa": db_row.description_fa if db_row else meta.get("description_fa"),
            "model_name": model_name,
            "base_url": base_url,
            "api_key": api_key,
            "provider": provider,
            "is_active": is_active,
            "extra_params": extra_params,
            "updated_at": updated_at,
            "has_custom_api_key": bool(db_row and db_row.api_key)
        }

    @classmethod
    async def get_all_section_configs(
        cls,
        db: AsyncSession
    ) -> List[SectionModelConfigDTO]:
        results = []
        for key in cls.SECTIONS_METADATA.keys():
            cfg = await cls.get_section_config(db, key)
            results.append(SectionModelConfigDTO(
                sectionKey=cfg["section_key"],
                sectionNameFa=cfg["section_name_fa"],
                descriptionFa=cfg.get("description_fa"),
                modelName=cfg["model_name"],
                baseUrl=cfg.get("base_url"),
                apiKeyMasked=cls.mask_api_key(cfg.get("api_key")),
                hasCustomApiKey=cfg.get("has_custom_api_key", False),
                provider=cfg.get("provider", "gemini"),
                isActive=cfg.get("is_active", True),
                extraParams=cfg.get("extra_params"),
                updatedAt=cfg.get("updated_at")
            ))
        return results

    @classmethod
    async def update_section_config(
        cls,
        db: AsyncSession,
        section_key: str,
        data: UpdateSectionModelConfigRequest
    ) -> SectionModelConfigDTO:
        meta = cls.SECTIONS_METADATA.get(section_key, {
            "name_fa": section_key,
            "description_fa": None,
            "default_model": lambda: settings.GEMINI_MODEL,
            "default_base_url": lambda: settings.GEMINI_BASE_URL,
            "default_api_key": lambda: settings.GEMINI_API_KEY,
            "default_provider": lambda: "gemini",
        })

        row = await db.scalar(select(AISectionConfig).where(AISectionConfig.section_key == section_key))
        if not row:
            row = AISectionConfig(
                section_key=section_key,
                section_name_fa=meta["name_fa"],
                description_fa=meta.get("description_fa"),
                model_name=data.modelName or meta["default_model"](),
                base_url=data.baseUrl or meta["default_base_url"](),
                api_key=data.apiKey or meta["default_api_key"](),
                provider=data.provider or meta["default_provider"](),
                is_active=data.isActive if data.isActive is not None else True,
                extra_params=data.extraParams or {}
            )
            db.add(row)
        else:
            if data.modelName is not None:
                row.model_name = data.modelName
            if data.baseUrl is not None:
                row.base_url = data.baseUrl
            if data.apiKey is not None and len(data.apiKey.strip()) > 0:
                row.api_key = data.apiKey.strip()
            if data.provider is not None:
                row.provider = data.provider
            if data.isActive is not None:
                row.is_active = data.isActive
            if data.extraParams is not None:
                row.extra_params = data.extraParams

        row.updated_at = utc_now()
        await db.commit()
        await db.refresh(row)

        return SectionModelConfigDTO(
            sectionKey=row.section_key,
            sectionNameFa=row.section_name_fa,
            descriptionFa=row.description_fa,
            modelName=row.model_name,
            baseUrl=row.base_url,
            apiKeyMasked=cls.mask_api_key(row.api_key),
            hasCustomApiKey=bool(row.api_key),
            provider=row.provider,
            isActive=row.is_active,
            extraParams=row.extra_params,
            updatedAt=int(row.updated_at.timestamp() * 1000)
        )

    @classmethod
    async def bulk_update_section_configs(
        cls,
        db: AsyncSession,
        data: BulkUpdateSectionModelConfigRequest
    ) -> List[SectionModelConfigDTO]:
        for sec in data.sections:
            if sec.sectionKey:
                await cls.update_section_config(db, sec.sectionKey, sec)
        return await cls.get_all_section_configs(db)

    @classmethod
    async def call_completion(
        cls,
        system_prompt: str,
        user_query: str,
        section_key: str = "chat",
        db: Optional[AsyncSession] = None,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Convenience wrapper around call_chat_generation for backward compatibility.
        """
        return await cls.call_chat_generation(
            section_key=section_key,
            system_prompt=system_prompt,
            user_query=user_query,
            db=db,
            model_override=model_override,
            temperature=temperature,
            max_tokens=max_tokens
        )

    @classmethod
    async def call_chat_generation(
        cls,
        section_key: str,
        system_prompt: str,
        user_query: str,
        db: Optional[AsyncSession] = None,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Executes chat generation with the effective model, base URL, and provider for this section.
        Returns None if not configured or failed (so caller can use local scholarly fallback).
        """
        cfg = await cls.get_section_config(db, section_key)
        if not cfg.get("is_active", True):
            return None

        model_name = model_override or cfg.get("model_name")
        base_url = (cfg.get("base_url") or "").rstrip("/")
        api_key = cfg.get("api_key") or ""
        provider = (cfg.get("provider") or "gemini").lower()

        if not api_key or len(api_key.strip()) < 5:
            return None

        # Determine candidate models to try in sequence with automatic failover
        candidate_models: List[str] = []
        if model_override:
            candidate_models.append(model_override)
        elif cfg.get("model_name"):
            candidate_models.append(cfg["model_name"])

        # Check configured fallback models (e.g. for Nvidia 3-model chain or custom section fallbacks)
        configured_fallbacks = (
            cfg.get("extra_params", {}).get("fallback_models")
            or (settings.NVIDIA_FALLBACK_MODELS if ("nvidia" in base_url or section_key == "chunk_representation") else [])
        )
        for fb in configured_fallbacks:
            if fb and fb not in candidate_models:
                candidate_models.append(fb)

        if not candidate_models:
            candidate_models = [cfg.get("model_name") or settings.GEMINI_MODEL]

        is_nvidia = "nvidia" in base_url or section_key == "chunk_representation"
        rpm_limit = int(cfg.get("extra_params", {}).get("rpm_limit") or settings.NVIDIA_RPM_LIMIT)
        rate_limiter = cls.get_rate_limiter(base_url, rpm_limit=rpm_limit) if is_nvidia else None

        timeout_sec = float(cfg.get("extra_params", {}).get("timeout", 90.0))
        client_timeout = httpx.Timeout(connect=20.0, read=timeout_sec, write=30.0, pool=20.0)

        # 1. OpenAI-compatible endpoint
        if (
            provider in ("openai", "openai_compatible")
            or "openai" in base_url
            or "openrouter" in base_url
            or "deepseek" in base_url
            or "nvidia" in base_url
            or "api/v1" in base_url
        ):
            endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
            eff_temp = temperature if temperature is not None else cfg.get("extra_params", {}).get("temperature", 0.7)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            for model_idx, curr_model in enumerate(candidate_models):
                payload: Dict[str, Any] = {
                    "model": curr_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    "temperature": eff_temp
                }
                if max_tokens is not None:
                    payload["max_tokens"] = max_tokens
                if response_format is not None:
                    payload["response_format"] = response_format

                max_retries = 2 if len(candidate_models) == 1 else 1
                for attempt in range(max_retries):
                    try:
                        if rate_limiter:
                            await rate_limiter.acquire()

                        async with httpx.AsyncClient(timeout=client_timeout, trust_env=True) as client:
                            resp = await client.post(endpoint, json=payload, headers=headers)
                            if resp.status_code == 200:
                                data = resp.json()
                                choices = data.get("choices", [])
                                if not choices:
                                    logger.warning(
                                        f"OpenAI-compatible response has empty 'choices' for model '{curr_model}' (section '{section_key}'): {data}"
                                    )
                                    break
                                msg = choices[0].get("message", {})
                                content = msg.get("content")
                                reasoning = msg.get("reasoning_content")

                                if content and content.strip():
                                    text_content = content.strip()
                                elif reasoning and reasoning.strip():
                                    text_content = reasoning.strip()
                                else:
                                    text_content = content or ""

                                if not text_content:
                                    logger.warning(
                                        f"Model '{curr_model}' returned empty text for section '{section_key}'. Trying fallback..."
                                    )
                                    break

                                usage = data.get("usage", {})
                                prompt_tokens = usage.get("prompt_tokens", len(user_query) // 3)
                                output_tokens = usage.get("completion_tokens", len(text_content) // 3)
                                return {
                                    "text": text_content,
                                    "model_used": curr_model,
                                    "usage": {
                                        "promptTokens": prompt_tokens,
                                        "outputTokens": output_tokens,
                                        "cachedTokens": 0
                                    }
                                }
                            elif resp.status_code == 429:
                                if rate_limiter:
                                    rate_limiter.record_429(backoff_seconds=2.0)
                                logger.warning(
                                    f"Rate limit (HTTP 429) hit on model '{curr_model}' for section '{section_key}'. "
                                    f"Failing over to next fallback model..."
                                )
                                await asyncio.sleep(1.0)
                                break
                            else:
                                logger.warning(
                                    f"Endpoint returned HTTP {resp.status_code} for model '{curr_model}' in section '{section_key}': {resp.text[:300]}. "
                                    f"Failing over to next fallback model..."
                                )
                                break
                    except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
                        if attempt == 0 and len(candidate_models) == 1:
                            logger.info(f"Call for model '{curr_model}' (section '{section_key}') encountered {type(e).__name__}; retrying once...")
                            await asyncio.sleep(1.5)
                            continue
                        logger.warning(
                            f"Call failed for model '{curr_model}' in section '{section_key}' [{type(e).__name__}]: {e}. "
                            f"Failing over to next model in chain..."
                        )
                        await asyncio.sleep(0.5)
                        break
                    except Exception as e:
                        logger.warning(
                            f"Unexpected error for model '{curr_model}' in section '{section_key}' [{type(e).__name__}]: {e}."
                        )
                        break

            logger.warning(f"All candidate models exhausted without success for section '{section_key}': {candidate_models}")
            return None

        # 2. Google Gemini native API format
        try:
            if not base_url:
                base_url = "https://generativelanguage.googleapis.com/v1beta"
            
            # Format: {base_url}/models/{model_name}:generateContent?key={api_key}
            if "/models/" in base_url:
                url = f"{base_url}:generateContent?key={api_key}"
            else:
                url = f"{base_url}/models/{model_name}:generateContent?key={api_key}"

            prompt_content = f"System Instructions:\n{system_prompt}\n\nپرسش کاربر:\n{user_query}" if system_prompt else user_query
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt_content}
                        ]
                    }
                ]
            }
            generation_config: Dict[str, Any] = {}
            if temperature is not None:
                generation_config["temperature"] = temperature
            elif cfg.get("extra_params", {}).get("temperature") is not None:
                generation_config["temperature"] = cfg.get("extra_params", {}).get("temperature")
            if max_tokens is not None:
                generation_config["maxOutputTokens"] = max_tokens
            if generation_config:
                payload["generationConfig"] = generation_config

            async with httpx.AsyncClient(timeout=client_timeout, trust_env=True) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        logger.warning(f"Gemini API returned no candidates for section '{section_key}': {data}")
                        return None
                    text_content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    usage_meta = data.get("usageMetadata", {})
                    p_tokens = usage_meta.get("promptTokenCount", max(10, len(user_query) // 3))
                    out_tokens = usage_meta.get("candidatesTokenCount", max(10, len(text_content) // 3))
                    c_tokens = usage_meta.get("cachedContentTokenCount", 0)
                    return {
                        "text": text_content,
                        "model_used": model_name,
                        "usage": {
                            "promptTokens": p_tokens,
                            "outputTokens": out_tokens,
                            "cachedTokens": c_tokens
                        }
                    }
                else:
                    logger.warning(f"Gemini API returned HTTP {resp.status_code} for section '{section_key}': {resp.text[:500]}")
                    return None
        except Exception as e:
            err_detail = str(e) or repr(e) or type(e).__name__
            logger.warning(f"Gemini API call failed for section '{section_key}' [{type(e).__name__}]: {err_detail}")
            return None

        return None

    @classmethod
    async def call_chat_with_tools(
        cls,
        section_key: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        db: Optional[AsyncSession] = None,
        model_override: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Executes chat generation with native function calling / OpenAI tools schema.
        Returns:
            {
                "text": str,
                "tool_calls": List[Dict[str, Any]],
                "finish_reason": str,
                "model_used": str,
                "usage": {"promptTokens": int, "outputTokens": int, "totalTokens": int}
            }
        """
        cfg = await cls.get_section_config(db, section_key)
        if not cfg.get("is_active", True):
            return None

        model_name = model_override or cfg.get("model_name")
        base_url = (cfg.get("base_url") or "").rstrip("/")
        api_key = cfg.get("api_key") or ""
        provider = (cfg.get("provider") or "gemini").lower()

        if not api_key or len(api_key.strip()) < 5:
            return None

        timeout_sec = float(cfg.get("extra_params", {}).get("timeout", 60.0))
        client_timeout = httpx.Timeout(connect=15.0, read=timeout_sec, write=25.0, pool=15.0)

        # 1. OpenAI-compatible endpoint (DeepSeek, etc.)
        if (
            provider in ("openai", "openai_compatible")
            or "openai" in base_url
            or "openrouter" in base_url
            or "deepseek" in base_url
            or "api/v1" in base_url
        ):
            endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
            eff_temp = temperature if temperature is not None else cfg.get("extra_params", {}).get("temperature", 0.3)
            payload: Dict[str, Any] = {
                "model": model_name,
                "messages": messages,
                "temperature": eff_temp
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = tool_choice
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            for attempt in range(2):
                try:
                    async with httpx.AsyncClient(timeout=client_timeout, trust_env=True) as client:
                        resp = await client.post(endpoint, json=payload, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            choices = data.get("choices", [])
                            if not choices:
                                logger.warning(f"OpenAI tools call returned empty choices for section '{section_key}': {data}")
                                return None
                            msg = choices[0].get("message", {})
                            text_content = msg.get("content") or ""
                            tool_calls = msg.get("tool_calls") or []
                            finish_reason = choices[0].get("finish_reason") or ("tool_calls" if tool_calls else "stop")

                            usage = data.get("usage", {})
                            prompt_tokens = usage.get("prompt_tokens", 50)
                            output_tokens = usage.get("completion_tokens", 50)
                            total_tokens = usage.get("total_tokens", prompt_tokens + output_tokens)

                            if db is not None:
                                try:
                                    from app.services.cost_service import CostService
                                    await CostService.calculate_and_log_usage(
                                        db=db,
                                        user_id=user_id,
                                        conversation_id=conversation_id,
                                        message_id=None,
                                        model_name=model_name,
                                        prompt_tokens=prompt_tokens,
                                        output_tokens=output_tokens,
                                        cached_tokens=0
                                    )
                                except Exception as log_err:
                                    logger.warning(f"Failed to log usage for section '{section_key}': {log_err}")

                            return {
                                "text": text_content,
                                "tool_calls": tool_calls,
                                "finish_reason": finish_reason,
                                "model_used": model_name,
                                "usage": {
                                    "promptTokens": prompt_tokens,
                                    "outputTokens": output_tokens,
                                    "totalTokens": total_tokens
                                }
                            }
                        else:
                            logger.warning(
                                f"OpenAI tools endpoint returned HTTP {resp.status_code} for section '{section_key}': {resp.text[:400]}"
                            )
                            return None
                except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as e:
                    if attempt == 0:
                        logger.info(f"OpenAI tools call for section '{section_key}' encountered {type(e).__name__}; retrying...")
                        await asyncio.sleep(1.0)
                        continue
                    logger.warning(f"OpenAI tools call failed for section '{section_key}' [{type(e).__name__}]: {e}")
                    return None
                except Exception as e:
                    logger.warning(f"OpenAI tools call exception for section '{section_key}' [{type(e).__name__}]: {e}")
                    return None

        return None

    @classmethod
    async def call_chat(
        cls,
        prompt: str,
        system_instruction: str = "",
        section_key: str = "chat",
        db: Optional[AsyncSession] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        model_override: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Executes a direct non-streaming chat completion and returns the generated text string.
        Convenience wrapper around call_chat_generation for representations, indexing, and text tasks.
        """
        sys_p = kwargs.get("system_prompt", system_instruction)
        user_p = kwargs.get("user_query", prompt)
        res_fmt = response_format or kwargs.get("response_format")
        res = await cls.call_chat_generation(
            section_key=section_key,
            system_prompt=sys_p,
            user_query=user_p,
            db=db,
            model_override=model_override,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=res_fmt
        )
        if res and res.get("text"):
            return ChatResponseStr(res["text"])
        return None

    @classmethod
    async def stream_chat_generation(
        cls,
        section_key: str,
        system_prompt: str,
        user_query: str,
        db: Optional[AsyncSession] = None,
        model_override: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams chat generation token-by-token from the configured provider (OpenAI-compatible or Gemini SSE).
        Yields:
          {"type": "token", "delta": "..."}
        And on completion:
          {"type": "done", "model_used": "...", "full_text": "...", "usage": {"promptTokens": ..., "outputTokens": ..., "cachedTokens": ...}}
        """
        cfg = await cls.get_section_config(db, section_key)
        if not cfg.get("is_active", True):
            return

        model_name = model_override or cfg.get("model_name")
        base_url = (cfg.get("base_url") or "").rstrip("/")
        api_key = cfg.get("api_key") or ""
        provider = (cfg.get("provider") or "gemini").lower()

        if not api_key or len(api_key.strip()) < 5:
            return

        is_nvidia = "nvidia" in base_url or section_key == "chunk_representation"
        rpm_limit = int(cfg.get("extra_params", {}).get("rpm_limit") or settings.NVIDIA_RPM_LIMIT)
        rate_limiter = cls.get_rate_limiter(base_url, rpm_limit=rpm_limit) if is_nvidia else None

        candidate_models: List[str] = []
        if model_override:
            candidate_models.append(model_override)
        elif cfg.get("model_name"):
            candidate_models.append(cfg["model_name"])

        configured_fallbacks = (
            cfg.get("extra_params", {}).get("fallback_models")
            or (settings.NVIDIA_FALLBACK_MODELS if is_nvidia else [])
        )
        for fb in configured_fallbacks:
            if fb and fb not in candidate_models:
                candidate_models.append(fb)

        if not candidate_models:
            candidate_models = [cfg.get("model_name") or settings.GEMINI_MODEL]

        # 1. OpenAI-compatible endpoint streaming
        if provider in ("openai", "openai_compatible") or "openai" in base_url or "openrouter" in base_url or "deepseek" in base_url or "nvidia" in base_url or "api/v1" in base_url:
            endpoint = f"{base_url}/chat/completions" if not base_url.endswith("/chat/completions") else base_url
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            for curr_model in candidate_models:
                payload = {
                    "model": curr_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    "temperature": cfg.get("extra_params", {}).get("temperature", 0.7),
                    "stream": True,
                    "stream_options": {"include_usage": True}
                }
                accumulated_text = []
                final_usage = None
                stream_started = False

                if rate_limiter:
                    await rate_limiter.acquire()

                try:
                    async with httpx.AsyncClient(timeout=60.0, trust_env=True) as client:
                        async with client.stream("POST", endpoint, json=payload, headers=headers) as resp:
                            if resp.status_code == 200:
                                async for raw_line in resp.aiter_lines():
                                    line = raw_line.strip()
                                    if not line or line.startswith(":"):
                                        continue
                                    if line.startswith("data: "):
                                        data_body = line[6:].strip()
                                        if data_body == "[DONE]":
                                            break
                                        try:
                                            chunk_data = json.loads(data_body)
                                            choices = chunk_data.get("choices", [])
                                            if choices:
                                                delta = choices[0].get("delta", {}).get("content", "")
                                                if delta:
                                                    stream_started = True
                                                    accumulated_text.append(delta)
                                                    yield {"type": "token", "delta": delta}
                                            if chunk_data.get("usage"):
                                                final_usage = chunk_data["usage"]
                                        except Exception:
                                            continue

                                if stream_started:
                                    full_text = "".join(accumulated_text)
                                    p_tokens = final_usage.get("prompt_tokens") if final_usage else max(10, len(user_query) // 3)
                                    o_tokens = final_usage.get("completion_tokens") if final_usage else max(10, len(full_text) // 3)
                                    yield {
                                        "type": "done",
                                        "model_used": curr_model,
                                        "full_text": full_text,
                                        "usage": {
                                            "promptTokens": p_tokens,
                                            "outputTokens": o_tokens,
                                            "cachedTokens": 0
                                        }
                                    }
                                    return
                            elif resp.status_code == 429:
                                if rate_limiter:
                                    rate_limiter.record_429(backoff_seconds=2.0)
                                logger.warning(
                                    f"Streaming rate limit (HTTP 429) on '{curr_model}' (section '{section_key}'). Falling over..."
                                )
                                await asyncio.sleep(1.0)
                                continue
                            else:
                                logger.warning(
                                    f"Streaming HTTP {resp.status_code} for '{curr_model}' (section '{section_key}'). Falling over..."
                                )
                                continue
                except Exception as e:
                    if stream_started:
                        logger.error(f"Stream interrupted for '{curr_model}': {e}")
                        return
                    logger.warning(
                        f"Stream connection failed for '{curr_model}' in section '{section_key}' [{type(e).__name__}]: {e}. Falling over..."
                    )
                    continue

            logger.error(f"All candidate models exhausted for streaming in section '{section_key}': {candidate_models}")
            return

        # 2. Google Gemini native API streaming
        try:
            if not base_url:
                base_url = "https://generativelanguage.googleapis.com/v1beta"

            if "/models/" in base_url:
                url = f"{base_url}:streamGenerateContent?alt=sse&key={api_key}"
            else:
                url = f"{base_url}/models/{model_name}:streamGenerateContent?alt=sse&key={api_key}"

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"System Instructions:\n{system_prompt}\n\nپرسش کاربر:\n{user_query}"}
                        ]
                    }
                ]
            }
            accumulated_text = []
            final_usage = None
            async with httpx.AsyncClient(timeout=60.0, trust_env=True) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code == 200:
                        async for raw_line in resp.aiter_lines():
                            line = raw_line.strip()
                            if not line or line.startswith(":"):
                                continue
                            if line.startswith("data: "):
                                data_body = line[6:].strip()
                                try:
                                    chunk_data = json.loads(data_body)
                                    candidates = chunk_data.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for p in parts:
                                            delta = p.get("text", "")
                                            if delta:
                                                accumulated_text.append(delta)
                                                yield {"type": "token", "delta": delta}
                                    if chunk_data.get("usageMetadata"):
                                        final_usage = chunk_data["usageMetadata"]
                                except Exception:
                                    continue

            full_text = "".join(accumulated_text)
            p_tokens = final_usage.get("promptTokenCount") if final_usage else max(10, len(user_query) // 3)
            o_tokens = final_usage.get("candidatesTokenCount") if final_usage else max(10, len(full_text) // 3)
            c_tokens = final_usage.get("cachedContentTokenCount", 0) if final_usage else 0
            yield {
                "type": "done",
                "model_used": model_name,
                "full_text": full_text,
                "usage": {
                    "promptTokens": p_tokens,
                    "outputTokens": o_tokens,
                    "cachedTokens": c_tokens
                }
            }
            return
        except Exception as e:
            err_detail = str(e) or repr(e) or type(e).__name__
            logger.warning(f"Gemini streaming failed for section '{section_key}' [{type(e).__name__}]: {err_detail}")
            return


    @classmethod
    async def call_embedding(
        cls,
        text: str,
        section_key: str = "embedding",
        db: Optional[AsyncSession] = None
    ) -> Optional[List[float]]:
        """
        Generates vector embedding for the given text using the configured section model and base URL,
        with deterministic semantic hashing fallback if offline or proxy fails.
        """
        # Fast offline / test mode check
        if os.environ.get("USE_OFFLINE_EMBEDDING") == "true":
            from app.services.vector_service import VectorService
            return VectorService._generate_fallback_vector(text)

        cfg = await cls.get_section_config(db, section_key)
        if not cfg.get("is_active", True):
            return None

        model_name = cfg.get("model_name") or settings.GEMINI_EMBEDDING_MODEL
        base_url = (cfg.get("base_url") or settings.GEMINI_BASE_URL).rstrip("/")
        api_key = cfg.get("api_key") or settings.GEMINI_API_KEY
        provider = (cfg.get("provider") or "gemini").lower()

        if not api_key or len(api_key.strip()) < 5 or api_key in ("mock", "offline") or model_name == "mock":
            if settings.EMBEDDING_OFFLINE_FALLBACK:
                from app.services.vector_service import VectorService
                return VectorService._generate_fallback_vector(text)
            return None

        # OpenAI-compatible embedding format (Avalai, OpenAI, etc.)
        if provider in ("openai", "openai_compatible") or "openai" in base_url or "avalai" in base_url or "api/v1" in base_url:
            try:
                endpoint = f"{base_url}/embeddings" if not base_url.endswith("/embeddings") else base_url
                payload = {
                    "model": model_name,
                    "input": text[:2000]
                }
                if "text-embedding-3" in model_name:
                    payload["dimensions"] = 768
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                timeout_val = getattr(settings, "EMBEDDING_HTTP_TIMEOUT", 3.0)
                async with httpx.AsyncClient(timeout=timeout_val, trust_env=True) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        values = data["data"][0]["embedding"]
                        return values
                    else:
                        logger.warning(f"OpenAI/Avalai embedding returned HTTP {resp.status_code}: {resp.text[:200]}")
                        if settings.EMBEDDING_OFFLINE_FALLBACK:
                            from app.services.vector_service import VectorService
                            return VectorService._generate_fallback_vector(text)
                        return None
            except Exception as e:
                err_detail = str(e) or repr(e) or type(e).__name__
                logger.warning(f"OpenAI/Avalai embedding call failed [{type(e).__name__}]: {err_detail}")
                if settings.EMBEDDING_OFFLINE_FALLBACK:
                    from app.services.vector_service import VectorService
                    return VectorService._generate_fallback_vector(text)
                return None

        # Gemini native format
        try:
            url = f"{base_url}/models/{model_name}:embedContent?key={api_key}"
            payload = {
                "model": f"models/{model_name}",
                "content": {
                    "parts": [{"text": text[:2000]}]
                }
            }
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    values = data.get("embedding", {}).get("values", [])
                    if values:
                        return values
        except Exception as e:
            logger.warning(f"Gemini embedding call failed: {e}")
            if settings.EMBEDDING_OFFLINE_FALLBACK:
                from app.services.vector_service import VectorService
                return VectorService._generate_fallback_vector(text)
            return None

        if settings.EMBEDDING_OFFLINE_FALLBACK:
            from app.services.vector_service import VectorService
            return VectorService._generate_fallback_vector(text)
        return None

    @classmethod
    async def call_embeddings_batch(
        cls,
        texts: List[str],
        section_key: str = "embedding",
        db: Optional[AsyncSession] = None
    ) -> List[Optional[List[float]]]:
        """
        Generates vector embeddings for a list of texts in batch using the configured section model and base URL.
        Supports native batching for OpenAI-compatible providers (like Avalai) and concurrent fallback.
        """
        if not texts:
            return []

        # Fast offline / test mode check
        if os.environ.get("USE_OFFLINE_EMBEDDING") == "true":
            from app.services.vector_service import VectorService
            return [VectorService._generate_fallback_vector(t) for t in texts]

        cfg = await cls.get_section_config(db, section_key)
        if not cfg.get("is_active", True):
            return [None] * len(texts)

        model_name = cfg.get("model_name") or settings.GEMINI_EMBEDDING_MODEL
        base_url = (cfg.get("base_url") or settings.GEMINI_BASE_URL).rstrip("/")
        api_key = cfg.get("api_key") or settings.GEMINI_API_KEY
        provider = (cfg.get("provider") or "gemini").lower()

        if not api_key or len(api_key.strip()) < 5:
            return [None] * len(texts)

        # OpenAI-compatible batch embedding format (Avalai, OpenAI, etc.)
        if provider in ("openai", "openai_compatible") or "openai" in base_url or "avalai" in base_url or "api/v1" in base_url:
            try:
                endpoint = f"{base_url}/embeddings" if not base_url.endswith("/embeddings") else base_url
                cleaned_inputs = [t[:2000] if (t and t.strip()) else "empty" for t in texts]
                payload: Dict[str, Any] = {
                    "model": model_name,
                    "input": cleaned_inputs
                }
                if "text-embedding-3" in model_name:
                    payload["dimensions"] = 768
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                async with httpx.AsyncClient(timeout=35.0, trust_env=True) as client:
                    resp = await client.post(endpoint, json=payload, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_items = data.get("data", [])
                        items_sorted = sorted(raw_items, key=lambda x: x.get("index", 0))
                        embeddings = [item.get("embedding") for item in items_sorted]
                        if len(embeddings) == len(texts):
                            return embeddings
                    else:
                        logger.warning(f"OpenAI/Avalai batch embedding HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                err_detail = str(e) or repr(e) or type(e).__name__
                logger.warning(f"OpenAI/Avalai batch embedding failed [{type(e).__name__}]: {err_detail}")

        # Concurrent individual call fallback
        tasks = [cls.call_embedding(t, section_key=section_key, db=db) for t in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r if (isinstance(r, list) and r) else None for r in results]

    @classmethod
    async def test_connection(
        cls,
        section_key: str,
        db: Optional[AsyncSession] = None,
        override: Optional[TestModelConnectionRequest] = None
    ) -> TestModelConnectionResponse:
        """
        Tests connectivity and response time for a section's configured or overridden model & base URL.
        """
        cfg = await cls.get_section_config(db, section_key)

        model_name = (override.modelName if override and override.modelName else None) or cfg["model_name"]
        base_url = ((override.baseUrl if override and override.baseUrl else None) or cfg["base_url"] or "").rstrip("/")
        api_key = (override.apiKey if override and override.apiKey else None) or cfg["api_key"] or ""
        provider = (override.provider if override and override.provider else None) or cfg["provider"] or "gemini"
        test_prompt = (override.testPrompt if override and override.testPrompt else None) or "سلام، لطفا اتصال را تایید کن."

        start_time = time.time()

        if not api_key or len(api_key.strip()) < 5:
            return TestModelConnectionResponse(
                sectionKey=section_key,
                modelName=model_name,
                baseUrl=base_url,
                provider=provider,
                success=False,
                message="کلید API تنظیم نشده است. لطفاً کلید API معتبر وارد نمایید.",
                latencyMs=0.0
            )

        try:
            # If embedding section
            if section_key == "embedding":
                emb = await cls.call_embedding(test_prompt, section_key=section_key, db=db)
                latency = round((time.time() - start_time) * 1000, 2)
                if emb and len(emb) > 0:
                    return TestModelConnectionResponse(
                        sectionKey=section_key,
                        modelName=model_name,
                        baseUrl=base_url,
                        provider=provider,
                        success=True,
                        message=f"اتصال به مدل تعبیه برداری با موفقیت برقرار شد (طول بردار: {len(emb)}).",
                        latencyMs=latency,
                        sampleResponse=f"Vector length: {len(emb)}, sample: {emb[:3]}..."
                    )
                else:
                    return TestModelConnectionResponse(
                        sectionKey=section_key,
                        modelName=model_name,
                        baseUrl=base_url,
                        provider=provider,
                        success=False,
                        message="تولید بردار از سرویس با شکست مواجه شد. لطفاً آدرس سرور و کلید دسترسی را بررسی فرمایید.",
                        latencyMs=latency
                    )

            # Chat / Text generation sections
            gen_res = await cls.call_chat_generation(
                section_key=section_key,
                system_prompt="پاسخ بسیار کوتاه و تک کلمه‌ای بده: سلام",
                user_query=test_prompt,
                db=db,
                model_override=model_name
            )
            latency = round((time.time() - start_time) * 1000, 2)

            if gen_res and gen_res.get("text"):
                return TestModelConnectionResponse(
                    sectionKey=section_key,
                    modelName=model_name,
                    baseUrl=base_url,
                    provider=provider,
                    success=True,
                    message="ارتباط با مدل با موفقیت برقرار شد و پاسخ دریافت گردید.",
                    latencyMs=latency,
                    sampleResponse=gen_res["text"][:150]
                )
            else:
                return TestModelConnectionResponse(
                    sectionKey=section_key,
                    modelName=model_name,
                    baseUrl=base_url,
                    provider=provider,
                    success=False,
                    message="پاسخی از مدل دریافت نشد. لطفاً آدرس Base URL و کلید API را بررسی کنید.",
                    latencyMs=latency
                )
        except Exception as e:
            latency = round((time.time() - start_time) * 1000, 2)
            return TestModelConnectionResponse(
                sectionKey=section_key,
                modelName=model_name,
                baseUrl=base_url,
                provider=provider,
                success=False,
                message=f"خطا در برقراری ارتباط: {str(e)}",
                latencyMs=latency
            )
