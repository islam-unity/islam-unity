from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AuthorDTO(BaseModel):
    id: str
    full_name: str
    avatar: Optional[str] = None
    role: str = "SEEKER"
    is_scholar: bool = False
    title: Optional[str] = None
    scholar_rank: Optional[int] = None
    madhhab: Optional[str] = None
    city: Optional[str] = None
    mosque: Optional[str] = None
    is_verified: bool = False


class PostMediaDTO(BaseModel):
    id: str
    media_type: str  # IMAGE, VIDEO, AUDIO
    media_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    aspect_ratio: str = "1:1"
    order: int = 0


class CommentDTO(BaseModel):
    id: str
    post_id: str
    author: AuthorDTO
    content: str
    is_scholar_reply: bool = False
    is_pinned: bool = False
    likes_count: int = 0
    is_liked_by_me: bool = False
    created_at: str
    replies: List["CommentDTO"] = []


class PostDTO(BaseModel):
    id: str
    title: Optional[str] = None
    content: str
    content_type: str = "MULTIMEDIA"
    category: str = "GENERAL"
    madhhab: Optional[str] = "مشترک"
    quran_references: List[Dict[str, Any]] = []
    hadith_references: List[Dict[str, Any]] = []
    tags: List[str] = []
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    saves_count: int = 0
    is_liked_by_me: bool = False
    is_saved_by_me: bool = False
    is_scholar_post: bool = False
    author: AuthorDTO
    media_items: List[PostMediaDTO] = []
    pinned_comment: Optional[CommentDTO] = None
    ai_summary: Optional[str] = None
    created_at: str


class FeedListResponse(BaseModel):
    items: List[PostDTO]
    total: int
    page: int
    limit: int
    has_more: bool


class CreateMediaItemDTO(BaseModel):
    media_type: str = "IMAGE"  # IMAGE, VIDEO, AUDIO
    media_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    aspect_ratio: str = "1:1"
    order: int = 0


class CreatePostRequest(BaseModel):
    title: Optional[str] = None
    content: str = Field(..., min_length=2, description="کپشن و متن اصلی پست")
    category: str = Field("GENERAL", description="دسته‌بندی موضوعی پست")
    madhhab: Optional[str] = Field("مشترک", description="مذهب یا مشترک")
    content_type: Optional[str] = Field("MULTIMEDIA", description="نوع محتوا")
    tags: List[str] = Field(default_factory=list, description="هشتگ‌های مرتبط")
    quran_references: List[Dict[str, Any]] = Field(default_factory=list, description="ارجاعات قرآنی")
    hadith_references: List[Dict[str, Any]] = Field(default_factory=list, description="ارجاعات روایی")
    media_items: List[CreateMediaItemDTO] = Field(default_factory=list, description="رسانه‌های ضمیمه")


class CreateCommentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000, description="متن نظر")
    parent_comment_id: Optional[str] = Field(None, description="شناسه نظر والد در صورت پاسخ")


class ReportPostRequest(BaseModel):
    reason: str = Field(..., description="دلیل گزارش تخلف")
    description: Optional[str] = Field(None, description="توضیحات تکمیلی گزارش")


class AIAssistCaptionRequest(BaseModel):
    draft_text: str = Field(..., min_length=3, description="پیش‌نویس اولیه کپشن یا موضوع پست")
    category: Optional[str] = Field("GENERAL", description="موضوع پست")
    tone: Optional[str] = Field("REVERENT_INSPIRING", description="لحن متن")
    generate_hashtags: bool = True


class AIAssistCaptionResponse(BaseModel):
    enhanced_caption: str
    suggested_title: str
    suggested_hashtags: List[str]
    suggested_quran_verse: Optional[Dict[str, Any]] = None
    suggested_hadith: Optional[Dict[str, Any]] = None
    appropriateness_check: Dict[str, Any]


class AIAnalyzePostResponse(BaseModel):
    post_id: str
    conceptual_summary: str
    key_themes: List[str]
    related_quran_verses: List[Dict[str, Any]]
    related_hadiths: List[Dict[str, Any]]
    sectarian_approximation_notes: str


class AuthorProfileDTO(BaseModel):
    author: AuthorDTO
    bio: Optional[str] = None
    posts_count: int = 0
    likes_count: int = 0
    followers_count: int = 0
    following_count: int = 0
    posts: List[PostDTO] = []
