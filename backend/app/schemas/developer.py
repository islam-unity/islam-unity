from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==========================================
# 1. Developer Account & Keys Schemas
# ==========================================

class DeveloperAccountCreateRequest(BaseModel):
    app_name: str = Field(..., min_length=2, max_length=128, description="نام پروژه یا اپلیکیشن دینی")
    description: Optional[str] = Field(None, max_length=500, description="توضیحات کوتاه درباره پروژه")


class DeveloperAccountDTO(BaseModel):
    id: str
    appName: str
    description: Optional[str] = None
    tier: str
    monthlyQuotaTokens: int
    usedTokensThisMonth: int
    remainingTokens: int
    rateLimitPerMinute: int
    isActive: bool
    createdAt: str


class CreateApiKeyRequest(BaseModel):
    label: Optional[str] = Field("کلید اصلی", max_length=64, description="برچسب یا عنوان کلید جهت یادآوری")


class ApiKeyCreatedResponse(BaseModel):
    id: str
    label: str
    key: str = Field(..., description="کلید کامل API - فقط یک بار نمایش داده می‌شود")
    keyPrefix: str
    createdAt: str


class ApiKeyDTO(BaseModel):
    id: str
    label: str
    keyPrefix: str
    totalRequests: int
    totalTokens: int
    lastUsedAt: Optional[str] = None
    isActive: bool
    createdAt: str


class DeveloperUsageDTO(BaseModel):
    accountId: str
    appName: str
    tier: str
    totalRequests: int
    totalTokensUsed: int
    monthlyQuota: int
    remainingQuota: int
    estimatedCostUsd: float
    estimatedCostIrr: float
    resetDate: Optional[str] = None


# ==========================================
# 2. OpenAI-Compatible Chat Completions
# ==========================================

class OpenAIChatMessage(BaseModel):
    role: str = Field(..., description="نقش پیام: system, user, assistant")
    content: str = Field(..., description="متن پیام")


class OpenAIChatCompletionRequest(BaseModel):
    model: Optional[str] = Field("ettehad-islamic-v1", description="مدل مدنظر")
    messages: List[OpenAIChatMessage] = Field(..., min_length=1, description="لیست پیام‌های گفتگو")
    temperature: Optional[float] = Field(0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: Optional[bool] = Field(False, description="استریم زنده پاسخ با فرمت SSE")
    extra_params: Optional[Dict[str, Any]] = Field(None, description="تنظیمات اختصاصی معارفی مانند madhab, tone, include_citations")


class OpenAIChatChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str


class OpenAIChatChoice(BaseModel):
    index: int = 0
    message: OpenAIChatChoiceMessage
    finish_reason: str = "stop"


class OpenAIUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAIChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChatChoice]
    citations: Optional[List[Dict[str, Any]]] = None
    usage: OpenAIUsage


# ==========================================
# 3. Specialized Islamic AI Schemas
# ==========================================

class DeveloperAskRequest(BaseModel):
    query: str = Field(..., min_length=3, description="پرسش فقهی، قرآنی یا معارفی")
    madhab: Optional[str] = Field("taqrib", description="مذهب فقهی: jafari, hanafi, shafii, maliki, hanbali, taqrib")
    tone: Optional[str] = Field("general", description="لحن پاسخ: youth, academic, general")
    source_filter: Optional[List[str]] = Field(None, description="فیلتر منابع: quran, hadith, tafsir, jurisprudence, all")
    stream: Optional[bool] = Field(False, description="فعال‌سازی استریم پاسخ")


class DeveloperAskResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = []
    suggestScholarEscalation: bool = False
    escalationCategory: Optional[str] = None
    referencedAyahs: List[Dict[str, Any]] = []
    referencedHadiths: List[Dict[str, Any]] = []
    modelUsed: str
    usage: OpenAIUsage


class DeveloperRAGSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="عبارت جستجوی مفهومی یا کلیدواژه معارفی")
    limit: Optional[int] = Field(5, ge=1, le=20)
    min_relevance_score: Optional[float] = Field(0.5, ge=0.0, le=1.0)


class DeveloperRAGSearchResultItem(BaseModel):
    chunkId: str
    bookTitle: str
    author: Optional[str] = None
    chapterTitle: Optional[str] = None
    volume: Optional[int] = None
    page: Optional[int] = None
    text: str
    score: float


# ==========================================
# 4. Developer Library Schemas
# ==========================================

class DeveloperLibrarySearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="عبارت جستجو در کتب")
    book_ids: Optional[List[str]] = Field(None, description="محدود کردن به شناسه‌های خاص کتاب")
    category_id: Optional[str] = Field(None, description="محدود کردن به دسته‌بندی خاص")
    search_mode: Optional[str] = Field("hybrid", description="حالت جستجو: text, vector, hybrid")
    limit: Optional[int] = Field(10, ge=1, le=50)


class DeveloperBookChatRequest(BaseModel):
    query: str = Field(..., min_length=2, description="پرسش درباره محتوای کتاب")
    stream: Optional[bool] = Field(False)
