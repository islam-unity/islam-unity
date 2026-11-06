from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ScholarDTO(BaseModel):
    id: str
    name: str
    title: str
    specialties: List[str]
    rating: float
    answerCount: int
    responseTimeHours: int
    rank: int
    avatarColorHex: str
    avatarUrl: Optional[str] = None
    isVerified: bool
    madhhab: str
    city: str
    mosque: str
    bio: str


class ScholarMetadataResponse(BaseModel):
    cities: List[str]
    mosques: List[str]
    madhhabs: List[str]
    specialties: List[str]


class AttachmentDTO(BaseModel):
    mediaId: str
    type: str  # VOICE, VIDEO, IMAGE, DOCUMENT
    title: str
    durationSeconds: Optional[int] = None
    fileUrl: str
    fileSizeBytes: int


class CreateThreadRequest(BaseModel):
    title: str
    initialQuestionBody: str
    category: str
    targetScholarId: Optional[str] = None
    isAnonymous: bool = False
    isPublic: bool = True
    isUrgent: bool = False
    attachments: Optional[List[AttachmentDTO]] = None


class CreateThreadResponse(BaseModel):
    threadId: str
    status: str
    createdAtFa: str
    trackingCode: str


class BookReferenceDTO(BaseModel):
    bookId: str
    bookTitle: str
    author: Optional[str] = None
    coverUrl: Optional[str] = None
    chapterId: Optional[str] = None
    chapterTitle: Optional[str] = None
    pageNumber: Optional[int] = None
    paragraphIndex: Optional[int] = None
    highlightedText: Optional[str] = None
    type: str = "PASSAGE_CITATION"  # BOOK_RECOMMENDATION or PASSAGE_CITATION


class ConsultationMessageDTO(BaseModel):
    id: str
    threadId: str
    senderId: str
    senderRole: str
    text: str
    citation: Optional[str] = None
    bookReference: Optional[BookReferenceDTO] = None
    attachment: Optional[AttachmentDTO] = None
    isRead: bool
    createdAt: str


class ThreadListItemDTO(BaseModel):
    id: str
    title: str
    category: str
    status: str
    trackingCode: str
    isUrgent: bool
    isBookmarked: bool
    isPublic: bool
    lastMessage: Optional[str] = None
    createdAtFa: str
    scholarName: Optional[str] = None


class ThreadDetailDTO(BaseModel):
    id: str
    title: str
    category: str
    status: str
    trackingCode: str
    isAnonymous: bool
    isPublic: bool
    isUrgent: bool
    isBookmarked: bool
    createdAt: str
    scholar: Optional[ScholarDTO] = None
    messages: List[ConsultationMessageDTO]
    attachments: List[AttachmentDTO]


class CreateMessageRequest(BaseModel):
    text: str
    citation: Optional[str] = None
    attachmentId: Optional[str] = None
    bookReference: Optional[BookReferenceDTO] = None


class ScholarCitationSuggestionItem(BaseModel):
    bookId: str
    bookTitle: str
    author: str
    coverUrl: Optional[str] = None
    chapterId: Optional[str] = None
    chapterTitle: Optional[str] = None
    pageNumber: Optional[int] = None
    paragraphIndex: Optional[int] = None
    quote: str
    relevanceReason: str
    confidenceScore: float = 0.95
    type: str = "PASSAGE_CITATION"


class UpdateThreadStatusRequest(BaseModel):
    status: str  # OPEN, CLOSED


class UpdateThreadVisibilityRequest(BaseModel):
    isPublic: bool


class QuickReplyDTO(BaseModel):
    id: str
    title: str
    content: str
    category: str


class CreateQuickReplyRequest(BaseModel):
    title: str
    content: str
    category: Optional[str] = "عمومی"
