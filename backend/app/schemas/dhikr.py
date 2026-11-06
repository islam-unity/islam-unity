from typing import Optional
from pydantic import BaseModel, Field


class DhikrCategoryCreate(BaseModel):
    id: Optional[str] = Field(None, description="شناسه یکتای دسته به انگلیسی (اختیاری)")
    title: str = Field(..., description="عنوان دسته‌بندی")
    description: Optional[str] = Field(None, description="توضیحات دسته‌بندی")
    icon: Optional[str] = Field("counter_3", description="آیکون Material Symbols")
    display_order: Optional[int] = Field(0, description="ترتیب نمایش")


class DhikrCategoryResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    icon: Optional[str] = "counter_3"
    display_order: int = 0
    is_system: bool = True


class DhikrCreate(BaseModel):
    title: str = Field(..., description="عنوان ذکر یا نیت دعا")
    arabic_text: str = Field(..., description="متن عربی یا عبارت ذکر")
    translation: Optional[str] = Field(None, description="ترجمه یا مفهوم ذکر")
    category: str = Field(..., description="شناسه دسته‌بندی")
    category_title: Optional[str] = Field(None, description="عنوان دسته‌بندی")
    target_count: Optional[int] = Field(100, description="تعداد دور پیش‌فرض یا هدف شمارش")
    virtue: Optional[str] = Field(None, description="فضیلت یا پاداش معنوی ذکر")
    source: Optional[str] = Field(None, description="منبع حدیثی یا مأخذ روایی")


class DhikrUpdate(BaseModel):
    title: Optional[str] = None
    arabic_text: Optional[str] = None
    translation: Optional[str] = None
    category: Optional[str] = None
    category_title: Optional[str] = None
    target_count: Optional[int] = None
    virtue: Optional[str] = None
    source: Optional[str] = None


class DhikrResponse(BaseModel):
    id: str
    title: str
    arabic_text: str
    translation: Optional[str] = ""
    category: str
    category_title: str
    target_count: int = 100
    virtue: Optional[str] = ""
    source: Optional[str] = ""
    is_system: bool = True
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
