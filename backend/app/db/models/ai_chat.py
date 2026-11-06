from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        Index("ix_ai_conversations_user_updated", "user_id", "updated_at"),
        Index("ix_ai_conversations_book_user", "book_id", "user_id"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=True, index=True)
    category = Column(String(128), default="عمومی", nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at")
    book = relationship("Book", foreign_keys=[book_id])


class AIMessage(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        Index("ix_ai_messages_conv_created", "conversation_id", "created_at"),
    )

    id = Column(String(64), primary_key=True, index=True)
    conversation_id = Column(String(64), ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False)  # USER, ASSISTANT
    content = Column(Text, nullable=False)
    referenced_ayahs = Column(JSON, default=list)  # [{"surahId": ..., "ayahNumber": ..., "text": "..."}]
    referenced_hadiths = Column(JSON, default=list)  # [{"source": "...", "text": "..."}]
    sources = Column(JSON, default=list)  # List of SourceCitationDTO dicts
    suggest_scholar_escalation = Column(Boolean, default=False)
    escalation_category = Column(String(128), nullable=True)
    is_liked = Column(Boolean, nullable=True)  # True, False, None
    feedback_text = Column(Text, nullable=True)
    token_usage = Column(JSON, default=dict)  # {"promptTokens": ..., "outputTokens": ..., "cachedTokens": ..., "totalTokens": ..., "costUsd": ..., "costIrr": ...}
    book_page_number = Column(Integer, nullable=True)
    book_chapter_id = Column(String(64), nullable=True)
    book_citation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    conversation = relationship("AIConversation", back_populates="messages")


class BookAICategory(Base):
    __tablename__ = "book_ai_categories"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(String(256), nullable=True)
    icon_name = Column(String(64), default="category")
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)


class PromptSuggestion(Base):
    __tablename__ = "ai_prompt_suggestions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    query = Column(Text, nullable=False)
    icon_name = Column(String(64), default="menu_book")
    order_index = Column(Integer, default=0)


class AIModelPricing(Base):
    __tablename__ = "ai_model_pricing"

    id = Column(String(64), primary_key=True, index=True)  # e.g. "gemini-1.5-flash", "default"
    model_name = Column(String(128), nullable=False)
    input_cost_per_million_usd = Column(Float, default=0.075, nullable=False)
    output_cost_per_million_usd = Column(Float, default=0.30, nullable=False)
    cached_cost_per_million_usd = Column(Float, default=0.01875, nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class SystemCurrencyConfig(Base):
    __tablename__ = "system_currency_config"

    id = Column(String(64), primary_key=True, default="primary_currency")
    usd_to_irr_rate = Column(Float, default=950000.0, nullable=False)  # 1 USD in Rials
    currency_name = Column(String(32), default="IRR")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index("ix_ai_usage_logs_user_created", "user_id", "created_at"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    conversation_id = Column(String(64), nullable=True, index=True)
    message_id = Column(String(64), nullable=True, index=True)
    model_name = Column(String(128), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    cached_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    cost_usd = Column(Float, default=0.0, nullable=False)
    cost_irr = Column(Float, default=0.0, nullable=False)
    exchange_rate_applied = Column(Float, default=950000.0, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)


class AISectionConfig(Base):
    """
    Holds model and base URL configuration separately for each section/component of the system.
    Sections:
    - 'chat': AI Chat & streaming conversation
    - 'embedding': Vector embeddings generation
    - 'agentic_rag': Agentic multi-query expansion and routing
    - 'jev': Fast decision engine & sufficiency evaluation
    - 'library': Book AI chat & chapter deep analysis
    - 'quran': Quranic Tadabbur & thematic insights
    - 'consultation': Scholar advice & response draft generation
    """
    __tablename__ = "ai_section_configs"

    section_key = Column(String(64), primary_key=True, index=True)
    section_name_fa = Column(String(128), nullable=False)
    description_fa = Column(String(256), nullable=True)
    model_name = Column(String(128), nullable=False)
    base_url = Column(String(512), nullable=True)
    api_key = Column(String(512), nullable=True)
    provider = Column(String(64), default="gemini", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    extra_params = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class UserMemory(Base):
    """
    Long-term user preferences and background context extracted securely:
    - MADHHAB: Reference jurisprudential school
    - LANGUAGE: Preferred language
    - KNOWLEDGE_LEVEL: Background level (GENERAL, INTERMEDIATE, SCHOLAR)
    - INTEREST: Topics of interest (e.g. Fiqh, Tafsir, Ethics)
    - UNRESOLVED_QUESTION: Questions pending or escalated
    Excludes sensitive/private personal details.
    """
    __tablename__ = "user_memories"
    __table_args__ = (
        Index("ix_user_memories_user_category", "user_id", "category"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    key = Column(String(128), nullable=False)
    value = Column(Text, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)
    source_conversation_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="memories")


class AgentTrace(Base):
    """
    Auditable trace log for every agent response:
    Records plan, tool calls, verifier evaluation, latency, tokens and costs.
    """
    __tablename__ = "agent_traces"
    __table_args__ = (
        Index("ix_agent_traces_conv_created", "conversation_id", "created_at"),
        Index("ix_agent_traces_user_created", "user_id", "created_at"),
    )

    id = Column(String(64), primary_key=True, index=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    message_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    user_query = Column(Text, nullable=False)
    mode = Column(String(32), default="agent", nullable=False)  # "agent" | "legacy"
    plan = Column(JSON, default=dict)
    tool_calls = Column(JSON, default=list)
    verification = Column(JSON, default=dict)
    total_latency_ms = Column(Float, default=0.0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now, index=True)
