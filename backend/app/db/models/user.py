from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, index=True)
    phone_number = Column(String(32), unique=True, index=True, nullable=False)
    full_name = Column(String(128), nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(32), default="SEEKER", nullable=False)  # SEEKER, SCHOLAR, ADMIN
    scholar_status = Column(String(32), default="NONE", nullable=False)  # NONE, PENDING, APPROVED, REJECTED
    mosque_name = Column(String(128), nullable=True)
    mosque_address = Column(String(256), nullable=True)
    madhhab = Column(String(64), default="شیعه اثناعشری", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Personalization & Demographics
    age = Column(Integer, nullable=True)
    gender = Column(String(16), nullable=True)  # MALE, FEMALE
    education = Column(String(64), nullable=True)
    interests = Column(JSON, default=list)  # List of interest tags e.g. ["TAFSIR", "AKHLAQ"]
    knowledge_level = Column(String(32), default="GENERAL")  # GENERAL, ACADEMIC, SEMINARY
    learning_goals = Column(Text, nullable=True)
    avatar = Column(String(256), nullable=True)
    
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    persona = relationship("PersonaConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    scholar_profile = relationship("Scholar", back_populates="user", uselist=False)
    threads = relationship("ConsultationThread", back_populates="user")
    bookmarks = relationship("QuranBookmark", back_populates="user")
    shelves = relationship("UserShelf", back_populates="user")
    highlights = relationship("BookHighlight", back_populates="user")
    reading_progress = relationship("ReadingProgress", back_populates="user")
    ai_conversations = relationship("AIConversation", back_populates="user")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
    developer_account = relationship("DeveloperAccount", back_populates="user", uselist=False, cascade="all, delete-orphan")


class PersonaConfig(Base):
    __tablename__ = "persona_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Bot Identity & Role
    bot_name = Column(String(64), default="دستیار معارفی اتحاد")
    bot_role_preset = Column(String(64), default="GENERAL_ASSISTANT")
    bot_avatar = Column(String(256), nullable=True)
    
    tone = Column(String(64), default="FRIENDLY_WARM")
    fiqh_approach = Column(String(64), default="APPROXIMATION_UNITY")
    detail_level = Column(String(64), default="STANDARD")
    include_ayah_address = Column(Boolean, default=True)
    include_hadith_references = Column(Boolean, default=True)
    custom_prompt_instructions = Column(Text, nullable=True)

    user = relationship("User", back_populates="persona")
