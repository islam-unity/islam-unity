from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LibraryPosterDTO(BaseModel):
    id: str
    title: str
    subtitle: Optional[str] = None
    imageUrl: str
    targetBookId: Optional[str] = None


class LibraryCategoryDTO(BaseModel):
    id: str
    title: str
    iconName: str
    bookCount: int = 0


class SubchapterSummaryDTO(BaseModel):
    id: Optional[str] = None
    title: str
    chunkCount: Optional[int] = 0


class ChapterSummaryDTO(BaseModel):
    id: str
    chapterNumber: int
    title: str
    readingTimeMinutes: int
    sectionTitle: Optional[str] = None
    subchapters: Optional[List[SubchapterSummaryDTO]] = None


class BookSummaryDTO(BaseModel):
    id: str
    title: str
    author: str
    coverUrl: Optional[str] = None
    categoryId: Optional[str] = None
    rating: float
    isFeatured: bool
    tags: List[str]
    topics: List[str] = Field(default_factory=list)
    pageCount: int
    language: Optional[str] = "fa"


class BookDetailDTO(BaseModel):
    id: str
    title: str
    author: str
    translator: Optional[str] = None
    publisher: Optional[str] = None
    publicationYear: Optional[str] = None
    coverUrl: Optional[str] = None
    categoryId: Optional[str] = None
    isFeatured: bool
    tags: List[str]
    topics: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    pageCount: int
    rating: float
    language: Optional[str] = "fa"
    chapters: List[ChapterSummaryDTO]


class ChapterDetailDTO(BaseModel):
    id: str
    bookId: str
    chapterNumber: int
    title: str
    readingTimeMinutes: int
    paragraphs: List[str]
    chunks: Optional[List[Dict[str, Any]]] = None
    subchapters: Optional[List[Dict[str, Any]]] = None


class ReadingProgressRequest(BaseModel):
    currentChapterId: Optional[str] = None
    currentParagraphIndex: int = 0
    percentage: float = Field(..., ge=0.0, le=100.0)


class CreateShelfRequest(BaseModel):
    title: str
    colorHex: Optional[str] = "#4CAF50"
    description: Optional[str] = None


class ShelfDTO(BaseModel):
    id: str
    title: str
    colorHex: str
    description: Optional[str] = None
    books: List[BookSummaryDTO] = []


class HighlightDTO(BaseModel):
    id: str
    bookId: str
    chapterId: Optional[str] = None
    selectedText: str
    note: Optional[str] = None
    colorHex: str
    createdAt: str


class CreateHighlightRequest(BaseModel):
    chapterId: Optional[str] = None
    selectedText: str
    note: Optional[str] = None
    colorHex: Optional[str] = "#FFE082"


class BookCitation(BaseModel):
    bookId: Optional[str] = None
    bookTitle: Optional[str] = None
    volume: Optional[int] = 1
    page: Optional[int] = 1
    chapterId: Optional[str] = None
    chapter: Optional[str] = None
    paragraphIndex: Optional[int] = None
    quote: str


class BookChatRequest(BaseModel):
    query: str
    conversationId: Optional[str] = None
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list)  # [{"role": "user"|"assistant", "content": "..."}]


class BookChatResponse(BaseModel):
    answer: str
    citations: List[BookCitation] = []
    conversationId: Optional[str] = None


class ChapterAnalysisRequest(BaseModel):
    bookId: str
    chapterId: str
    analysisType: str  # SUMMARY, EXPLAIN_TERMS, CROSS_REFERENCES, PRACTICAL_LESSONS, REFLECTIVE_QUIZ


class ChapterAnalysisResponse(BaseModel):
    analysisType: str
    result: Any


class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    categoryId: Optional[str] = None


class SemanticSearchResultItem(BaseModel):
    bookId: str
    bookTitle: str
    author: Optional[str] = None
    coverUrl: Optional[str] = None
    categoryTitle: Optional[str] = None
    chapterId: Optional[str] = None
    chapterTitle: Optional[str] = None
    excerpt: str
    relevanceScore: float
    reasoning: str
    topics: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    matchType: Optional[str] = "HYBRID_VECTOR_SQL"


class ReaderContextualAIRequest(BaseModel):
    chapterId: str
    paragraphIndex: Optional[int] = None
    selectedText: str
    actionType: Optional[str] = "CUSTOM_QUERY"  # EXPLAIN, SUMMARIZE, TRANSLATE_IRAB, PRACTICAL_LESSONS, CUSTOM_QUERY
    userQuery: Optional[str] = None
    conversationId: Optional[str] = None
    saveAsHighlight: Optional[bool] = False
    colorHex: Optional[str] = "#FFE082"


class BookSubmissionCreateRequest(BaseModel):
    type: str = "SUBMIT_NEW"  # SUBMIT_NEW or REQUEST_EXISTING
    title: str
    author: Optional[str] = None
    translator: Optional[str] = None
    publisher: Optional[str] = None
    category: Optional[str] = None
    isbn: Optional[str] = None
    fileUrl: Optional[str] = None
    coverUrl: Optional[str] = None
    submissionType: Optional[str] = "FREE"  # WAQF_FREE, OPEN_ACCESS, REVIEW, GENERAL
    description: Optional[str] = None
    userName: Optional[str] = None
    userContact: Optional[str] = None


class BookSubmissionResponse(BaseModel):
    id: str
    type: str
    title: str
    author: Optional[str] = None
    translator: Optional[str] = None
    publisher: Optional[str] = None
    category: Optional[str] = None
    isbn: Optional[str] = None
    fileUrl: Optional[str] = None
    coverUrl: Optional[str] = None
    submissionType: Optional[str] = None
    description: Optional[str] = None
    trackingCode: str
    status: str
    adminNotes: Optional[str] = None
    createdAt: str
    updatedAt: Optional[str] = None
    userName: Optional[str] = None
    userContact: Optional[str] = None


class BookSubmissionStatusUpdateRequest(BaseModel):
    status: str  # PENDING, IN_REVIEW, APPROVED, AVAILABLE, REJECTED
    adminNotes: Optional[str] = None


# --- BOOK AI SESSION, CATEGORY & MASTER AGENT DTOs ---

class BookAICategoryDTO(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    iconName: Optional[str] = "category"
    isSystem: bool = False


class BookAICategoryCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    iconName: Optional[str] = "category"


class BookAISessionCreateRequest(BaseModel):
    title: str
    category: Optional[str] = "عمومی"


class BookAISessionDTO(BaseModel):
    id: str
    title: str
    bookId: str
    category: str
    messageCount: int = 0
    createdAt: str
    updatedAt: str


class BookAIMessageDTO(BaseModel):
    id: str
    conversationId: str
    role: str
    content: str
    bookPageNumber: Optional[int] = None
    bookChapterId: Optional[str] = None
    bookCitation: Optional[str] = None
    createdAt: str


class MasterAgentCrossBookQueryRequest(BaseModel):
    query: str
    category: Optional[str] = None
    bookIds: Optional[List[str]] = None


class MasterAgentCrossBookResponse(BaseModel):
    query: str
    summary: str
    analyzedBookCount: int
    matchedQuestionsCount: int
    topCategories: List[str]
    citations: List[Dict[str, Any]]
    synthesizedAnswer: str


class BookReviewDTO(BaseModel):
    id: str
    bookId: str
    author: str
    avatar: Optional[str] = None
    rating: float = 5.0
    time: Optional[str] = None
    content: str
    isApproved: bool = True
    status: Optional[str] = "approved"


class CreateBookReviewRequest(BaseModel):
    rating: float = 5.0
    content: str
    authorName: Optional[str] = None




