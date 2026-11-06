import uuid
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, func, Index
from app.db.base import Base


class DhikrCategory(Base):
    __tablename__ = "dhikr_categories"

    id = Column(String(64), primary_key=True, index=True) # e.g. "daily", "taqibat", "hajat", "ziyarat", "munajat", "custom"
    title = Column(String(128), nullable=False) # e.g. "اذکار ایام هفته", "تعقیبات نماز"
    description = Column(String(256), nullable=True)
    icon = Column(String(64), default="counter_3")
    display_order = Column(Integer, default=0)
    is_system = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "icon": self.icon or "counter_3",
            "display_order": self.display_order,
            "is_system": self.is_system,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Dhikr(Base):
    __tablename__ = "dhikrs"
    __table_args__ = (
        Index("ix_dhikrs_cat_system", "category", "is_system"),
    )

    id = Column(String(64), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(256), nullable=False, index=True) # e.g. "ذکر یونسیه", "صلوات بر پیامبر و آل"
    arabic_text = Column(Text, nullable=False)
    translation = Column(Text, nullable=True)
    category = Column(String(64), nullable=False, index=True) # matches DhikrCategory.id
    category_title = Column(String(128), nullable=False)
    target_count = Column(Integer, default=100) # e.g. 100, 33, 7, 14, 40, 313
    virtue = Column(Text, nullable=True) # فضیلت و ثواب
    source = Column(String(256), nullable=True) # منبع حدیثی
    is_system = Column(Boolean, default=True) # True = Admin/System, False = User Custom
    user_id = Column(String(64), nullable=True, index=True) # If user custom

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "arabic_text": self.arabic_text,
            "translation": self.translation or "",
            "category": self.category,
            "category_title": self.category_title,
            "target_count": self.target_count or 100,
            "virtue": self.virtue or "",
            "source": self.source or "",
            "is_system": self.is_system,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
