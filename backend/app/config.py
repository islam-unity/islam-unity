from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "اپلیکیشن جامع معارفی اتحاد"
    API_V1_STR: str = "/v1"
    SECRET_KEY: str = "ettehad-super-secret-jwt-key-2026-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days

    DATABASE_URL: str = "postgresql+asyncpg://postgres:1234@localhost:5432/ettehad_db"

    # SMS Configuration (Melipayamak OTP)
    SMS_USERNAME: str = "9919699504"
    SMS_PASSWORD: str = "A1@DL"
    VERIFICATION_BODY_ID: int = 374402


    # Default / Global AI Settings
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"

    # User-Specified AI Provider Aliases
    DEEPSEEK_API_KEY_UNITY: str = ""
    DEEPSEEK_BASE_URL_UNITY: str = "https://api.deepseek.com"
    MODEL_DEEPPSEEK_LLM_UNITY: str = "deepseek-chat"

    AVALAI_BASE_URL_UNITY: str = "https://api.avalai.ir/v1"
    AVALAI_API_KEY: str = ""
    AVALAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    TYPESAFE_API_KEY: str = ""

    # NVIDIA Provider Aliases (Background Chunk Processing & Offline Non-urgent Tasks)
    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL_BOLT: str = "nvidia/nemotron-3.5-bolt-e4b"
    NVIDIA_MODEL_SUPER_VL: str = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    NVIDIA_MODEL_MISTRAL_LARGE: str = "mistralai/mistral-large-4-1t-a52b"
    NVIDIA_DEFAULT_MODEL: str = "nvidia/nemotron-3.5-bolt-e4b"
    NVIDIA_RPM_LIMIT: int = 40
    NVIDIA_FALLBACK_MODELS: List[str] = [
        "nvidia/nemotron-3.5-bolt-e4b",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
        "mistralai/mistral-large-4-1t-a52b"
    ]

    # Per-Section AI Model & Base URL Settings
    # 1. AI Chat & Streaming
    AI_CHAT_MODEL: str = "deepseek-chat"
    AI_CHAT_BASE_URL: str = "https://api.deepseek.com"
    AI_CHAT_API_KEY: str = ""
    AI_CHAT_PROVIDER: str = "openai_compatible"

    # 2. Vector Embeddings & Semantic Search
    AI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_EMBEDDING_BASE_URL: str = "https://api.avalai.ir/v1"
    AI_EMBEDDING_API_KEY: str = ""
    AI_EMBEDDING_PROVIDER: str = "openai_compatible"

    # 3. Agentic RAG (Routing, Multi-Query, Reflection)
    AI_AGENTIC_RAG_MODEL: str = "deepseek-chat"
    AI_AGENTIC_RAG_BASE_URL: str = "https://api.deepseek.com"
    AI_AGENTIC_RAG_API_KEY: str = ""
    AI_AGENTIC_RAG_PROVIDER: str = "openai_compatible"

    # 4. JEV (TypeSafe AI System One decision model)
    JEV_API_KEY: str = ""
    JEV_API_URL: str = "https://api.typesafe.ai/v1/systemone"
    JEV_BASE_URL: str = "https://api.typesafe.ai/v1/systemone"
    JEV_MODEL: str = "jev-latest"
    JEV_PROVIDER: str = "jev_systemone"

    # 5. Library AI (Book Chat & Chapter Analysis)
    AI_LIBRARY_MODEL: str = "deepseek-chat"
    AI_LIBRARY_BASE_URL: str = "https://api.deepseek.com"
    AI_LIBRARY_API_KEY: str = ""
    AI_LIBRARY_PROVIDER: str = "openai_compatible"

    # 6. Quran AI (Tadabbur & Thematic Insights)
    AI_QURAN_MODEL: str = "deepseek-chat"
    AI_QURAN_BASE_URL: str = "https://api.deepseek.com"
    AI_QURAN_API_KEY: str = ""
    AI_QURAN_PROVIDER: str = "openai_compatible"

    # 7. Scholar Consultation AI Assistant
    AI_CONSULTATION_MODEL: str = "deepseek-chat"
    AI_CONSULTATION_BASE_URL: str = "https://api.deepseek.com"
    AI_CONSULTATION_API_KEY: str = ""
    AI_CONSULTATION_PROVIDER: str = "openai_compatible"

    # 8. Chunk Processing & Background Representation Engine (NVIDIA)
    AI_CHUNK_REPRESENTATION_MODEL: str = "nvidia/nemotron-3.5-bolt-e4b"
    AI_CHUNK_REPRESENTATION_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    AI_CHUNK_REPRESENTATION_API_KEY: str = ""
    AI_CHUNK_REPRESENTATION_PROVIDER: str = "openai_compatible"

    # Agent Engine (Planner, ReAct Executor, Verifier, Memory)
    AI_AGENT_MODE: str = "agent"  # "agent" | "legacy"
    EMBEDDING_OFFLINE_FALLBACK: bool = True
    EMBEDDING_HTTP_TIMEOUT: float = 3.0

    AI_AGENT_PLANNER_MODEL: str = "deepseek-chat"
    AI_AGENT_PLANNER_BASE_URL: str = "https://api.deepseek.com"
    AI_AGENT_PLANNER_API_KEY: str = ""
    AI_AGENT_PLANNER_PROVIDER: str = "openai_compatible"

    AI_AGENT_EXECUTOR_MODEL: str = "deepseek-chat"
    AI_AGENT_EXECUTOR_BASE_URL: str = "https://api.deepseek.com"
    AI_AGENT_EXECUTOR_API_KEY: str = ""
    AI_AGENT_EXECUTOR_PROVIDER: str = "openai_compatible"

    AI_AGENT_VERIFIER_MODEL: str = "deepseek-chat"
    AI_AGENT_VERIFIER_BASE_URL: str = "https://api.deepseek.com"
    AI_AGENT_VERIFIER_API_KEY: str = ""
    AI_AGENT_VERIFIER_PROVIDER: str = "openai_compatible"

    AI_AGENT_MEMORY_MODEL: str = "deepseek-chat"
    AI_AGENT_MEMORY_BASE_URL: str = "https://api.deepseek.com"
    AI_AGENT_MEMORY_API_KEY: str = ""
    AI_AGENT_MEMORY_PROVIDER: str = "openai_compatible"

    # Qdrant Vector DB
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "islamic_knowledge"
    QDRANT_USE_MEMORY_FALLBACK: bool = True

    # Token Pricing & Currency (USD & IRR)
    USD_TO_IRR_RATE: float = 950000.0  # نرخ هر دلار به ریال (قابل تغییر در پنل ادمین)
    DEFAULT_INPUT_COST_PER_M: float = 0.075  # هزینه هر ۱ میلیون توکن ورودی ($)
    DEFAULT_OUTPUT_COST_PER_M: float = 0.30  # هزینه هر ۱ میلیون توکن خروجی ($)
    DEFAULT_CACHED_COST_PER_M: float = 0.01875  # هزینه هر ۱ میلیون توکن کش‌شده ($)

    UPLOAD_DIR: str = "./media/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 26214400  # 25 MB
    STATIC_URL_PREFIX: str = "/media"

    CORS_ORIGINS: List[str] = ["*"]

    @model_validator(mode="after")
    def sync_provider_mappings(self):
        # 1. Wire DeepSeek for Chat & Generation sections
        ds_key = self.DEEPSEEK_API_KEY_UNITY or self.AI_CHAT_API_KEY
        ds_model = self.MODEL_DEEPPSEEK_LLM_UNITY or self.AI_CHAT_MODEL or "deepseek-flash"
        ds_url = self.DEEPSEEK_BASE_URL_UNITY or self.AI_CHAT_BASE_URL or "https://api.deepseek.com"

        if ds_key:
            if not self.AI_CHAT_API_KEY:
                self.AI_CHAT_API_KEY = ds_key
            if not self.AI_CHAT_MODEL or self.AI_CHAT_MODEL == "gemini-1.5-flash":
                self.AI_CHAT_MODEL = ds_model
            if not self.AI_CHAT_BASE_URL or "generativelanguage" in self.AI_CHAT_BASE_URL:
                self.AI_CHAT_BASE_URL = ds_url
            self.AI_CHAT_PROVIDER = "openai_compatible"

            for prefix in (
                "AI_AGENTIC_RAG", "AI_LIBRARY", "AI_QURAN", "AI_CONSULTATION",
                "AI_AGENT_PLANNER", "AI_AGENT_EXECUTOR", "AI_AGENT_VERIFIER", "AI_AGENT_MEMORY"
            ):
                if not getattr(self, f"{prefix}_API_KEY"):
                    setattr(self, f"{prefix}_API_KEY", ds_key)
                if getattr(self, f"{prefix}_MODEL") in ("", "gemini-1.5-flash"):
                    setattr(self, f"{prefix}_MODEL", ds_model)
                if not getattr(self, f"{prefix}_BASE_URL") or "generativelanguage" in getattr(self, f"{prefix}_BASE_URL"):
                    setattr(self, f"{prefix}_BASE_URL", ds_url)
                setattr(self, f"{prefix}_PROVIDER", "openai_compatible")

        # 2. Wire Avalai ONLY for Vector Embeddings
        av_key = self.AVALAI_API_KEY or self.AI_EMBEDDING_API_KEY
        av_url = self.AVALAI_BASE_URL_UNITY or self.AI_EMBEDDING_BASE_URL or "https://api.avalai.ir/v1"
        av_model = self.AVALAI_EMBEDDING_MODEL or self.AI_EMBEDDING_MODEL or "text-embedding-3-small"

        if av_key:
            if not self.AI_EMBEDDING_API_KEY:
                self.AI_EMBEDDING_API_KEY = av_key
            if not self.AI_EMBEDDING_MODEL or self.AI_EMBEDDING_MODEL == "text-embedding-004":
                self.AI_EMBEDDING_MODEL = av_model
            if not self.AI_EMBEDDING_BASE_URL or "generativelanguage" in self.AI_EMBEDDING_BASE_URL:
                self.AI_EMBEDDING_BASE_URL = av_url
            self.AI_EMBEDDING_PROVIDER = "openai_compatible"

        # 3. Wire TypeSafe for JEV System One Decision Engine
        ts_key = self.TYPESAFE_API_KEY or self.JEV_API_KEY
        if ts_key:
            if not self.JEV_API_KEY:
                self.JEV_API_KEY = ts_key
            if not self.TYPESAFE_API_KEY:
                self.TYPESAFE_API_KEY = ts_key
            if not self.JEV_MODEL or self.JEV_MODEL == "systemone-v1":
                self.JEV_MODEL = "jev-latest"
            if not self.JEV_BASE_URL:
                self.JEV_BASE_URL = "https://api.typesafe.ai/v1/systemone"
            if not self.JEV_API_URL:
                self.JEV_API_URL = "https://api.typesafe.ai/v1/systemone"
            self.JEV_PROVIDER = "jev_systemone"

        # 4. Wire NVIDIA for Background Chunk Processing & Chunk Representation
        nv_key = self.NVIDIA_API_KEY or self.AI_CHUNK_REPRESENTATION_API_KEY
        nv_url = self.NVIDIA_BASE_URL or self.AI_CHUNK_REPRESENTATION_BASE_URL or "https://integrate.api.nvidia.com/v1"
        nv_model = self.NVIDIA_DEFAULT_MODEL or self.AI_CHUNK_REPRESENTATION_MODEL or "nvidia/nemotron-3.5-bolt-e4b"

        if nv_key:
            if not self.AI_CHUNK_REPRESENTATION_API_KEY:
                self.AI_CHUNK_REPRESENTATION_API_KEY = nv_key
            if not self.AI_CHUNK_REPRESENTATION_MODEL:
                self.AI_CHUNK_REPRESENTATION_MODEL = nv_model
            if not self.AI_CHUNK_REPRESENTATION_BASE_URL:
                self.AI_CHUNK_REPRESENTATION_BASE_URL = nv_url
            self.AI_CHUNK_REPRESENTATION_PROVIDER = "openai_compatible"

        return self

    model_config = SettingsConfigDict(
        env_file=[".env", "backend/.env", "../.env"],
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
