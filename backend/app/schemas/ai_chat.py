from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConversationListItemDTO(BaseModel):
    id: str
    title: str
    lastMessage: Optional[str] = None
    messageCount: int = 0
    updatedAt: int


class CreateConversationRequest(BaseModel):
    title: str
    initialQuery: Optional[str] = None


class CreateConversationResponse(BaseModel):
    conversationId: str
    createdAt: int


class OverridePersonaDTO(BaseModel):
    botName: Optional[str] = None
    botRolePreset: Optional[str] = None
    botAvatar: Optional[str] = None
    tone: Optional[str] = "FRIENDLY_WARM"
    fiqhApproach: Optional[str] = "APPROXIMATION_UNITY"
    detailLevel: Optional[str] = "STANDARD"
    includeAyahAddress: Optional[bool] = True
    includeHadithReferences: Optional[bool] = True
    customPromptInstructions: Optional[str] = None


class ReferencedAyahDTO(BaseModel):
    surahId: int
    ayahNumber: int
    text: str


class ReferencedHadithDTO(BaseModel):
    source: str
    text: str


class SourceCitationDTO(BaseModel):
    index: int
    type: str  # QURAN, BOOK, HADITH, CONSULTATION
    title: str
    targetUrl: str
    excerpt: Optional[str] = None
    madhhab: Optional[str] = None
    pageNumber: Optional[int] = None
    score: Optional[float] = None
    language: Optional[str] = "fa"
    originalLanguage: Optional[str] = None
    isTranslated: Optional[bool] = False
    originalTitle: Optional[str] = None


class TokenUsageDTO(BaseModel):
    modelName: Optional[str] = None
    promptTokens: int = 0
    outputTokens: int = 0
    cachedTokens: int = 0
    totalTokens: int = 0
    costUsd: float = 0.0
    costIrr: float = 0.0
    currency: str = "IRR"
    latencyBreakdown: Optional[Dict[str, float]] = None


class SendAIMessageRequest(BaseModel):
    content: str
    overridePersona: Optional[OverridePersonaDTO] = None
    overrideModel: Optional[str] = None
    model: Optional[str] = None
    targetLanguage: Optional[str] = None
    excludePreviousSources: Optional[bool] = None
    targetBookId: Optional[str] = None
    targetScholarId: Optional[str] = None
    forceScholarEscalation: Optional[bool] = None


class AIMessageDTO(BaseModel):
    messageId: str
    conversationId: str
    role: str
    content: str
    referencedAyahs: List[ReferencedAyahDTO] = []
    referencedHadiths: List[ReferencedHadithDTO] = []
    sources: List[SourceCitationDTO] = []
    suggestScholarEscalation: bool = False
    escalationCategory: Optional[str] = None
    recommendedScholar: Optional[Dict[str, Any]] = None
    recommendedBook: Optional[Dict[str, Any]] = None
    aiCapabilityStatus: Optional[str] = "SELF_SUFFICIENT"  # SELF_SUFFICIENT, SCHOLAR_ESCALATED, BOOK_RECOMMENDED, COMPREHENSIVE
    routingAssessment: Optional[Dict[str, Any]] = None
    tokenUsage: Optional[TokenUsageDTO] = None
    latencyBreakdown: Optional[Dict[str, float]] = None
    timestamp: int
    isLiked: Optional[bool] = None


class ModelPricingDTO(BaseModel):
    modelName: str
    inputCostPerMillionUsd: float
    outputCostPerMillionUsd: float
    cachedCostPerMillionUsd: float
    isActive: bool = True


class CostConfigDTO(BaseModel):
    usdToIrrRate: float
    currencyName: str = "IRR"
    modelsPricing: List[ModelPricingDTO] = []


class UpdateModelPricingRequest(BaseModel):
    modelName: str
    inputCostPerMillionUsd: float
    outputCostPerMillionUsd: float
    cachedCostPerMillionUsd: float
    isActive: Optional[bool] = True


class UpdateCostConfigRequest(BaseModel):
    usdToIrrRate: Optional[float] = None
    currencyName: Optional[str] = "IRR"
    modelsPricing: Optional[List[UpdateModelPricingRequest]] = None


class UsageStatsDTO(BaseModel):
    totalRequests: int = 0
    totalPromptTokens: int = 0
    totalOutputTokens: int = 0
    totalCachedTokens: int = 0
    totalTokens: int = 0
    totalCostUsd: float = 0.0
    totalCostIrr: float = 0.0
    usdToIrrRate: float = 950000.0
    recentLogs: List[Dict[str, Any]] = []


class PersonaConfigDTO(BaseModel):
    botName: str = "دستیار معارفی اتحاد"
    botRolePreset: str = "GENERAL_ASSISTANT"
    botAvatar: Optional[str] = None
    tone: str = "FRIENDLY_WARM"
    fiqhApproach: str = "APPROXIMATION_UNITY"
    detailLevel: str = "STANDARD"
    includeAyahAddress: bool = True
    includeHadithReferences: bool = True
    customPromptInstructions: Optional[str] = None


class PromptSuggestionDTO(BaseModel):
    title: str
    query: str
    iconName: str


class MessageFeedbackRequest(BaseModel):
    isLiked: Optional[bool] = None
    feedbackText: Optional[str] = None


class SectionModelConfigDTO(BaseModel):
    sectionKey: str
    sectionNameFa: str
    descriptionFa: Optional[str] = None
    modelName: str
    baseUrl: Optional[str] = None
    apiKeyMasked: Optional[str] = None
    hasCustomApiKey: bool = False
    provider: str = "gemini"
    isActive: bool = True
    extraParams: Optional[Dict[str, Any]] = None
    updatedAt: Optional[int] = None


class UpdateSectionModelConfigRequest(BaseModel):
    sectionKey: Optional[str] = None
    modelName: Optional[str] = None
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    provider: Optional[str] = None
    isActive: Optional[bool] = None
    extraParams: Optional[Dict[str, Any]] = None


class BulkUpdateSectionModelConfigRequest(BaseModel):
    sections: List[UpdateSectionModelConfigRequest]


class TestModelConnectionRequest(BaseModel):
    modelName: Optional[str] = None
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    provider: Optional[str] = None
    testPrompt: Optional[str] = "سلام، لطفا اتصال مدل را تایید کن."


class TestModelConnectionResponse(BaseModel):
    sectionKey: Optional[str] = None
    modelName: str
    baseUrl: Optional[str] = None
    provider: str
    success: bool
    message: str
    latencyMs: float = 0.0
    sampleResponse: Optional[str] = None
