from sqlalchemy import Column, String, Float, Integer, Boolean, Text, ForeignKey, JSON, DateTime, func, Index
from sqlalchemy.orm import relationship
from app.db.base import Base


class Scholar(Base):
    __tablename__ = "scholars"
    __table_args__ = (
        Index("ix_scholars_city_madhhab", "city", "madhhab"),
        Index("ix_scholars_rank_rating", "rank", "rating"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    specialties = Column(JSON, default=list)  # List of string specialties
    rating = Column(Float, default=5.0)
    answer_count = Column(Integer, default=0)
    response_time_hours = Column(Integer, default=4)
    rank = Column(Integer, default=1)
    avatar_color_hex = Column(String(32), default="0xFF8C6239")
    avatar_url = Column(String(512), nullable=True)
    is_verified = Column(Boolean, default=True)
    madhhab = Column(String(64), nullable=False, index=True)
    city = Column(String(64), nullable=False, index=True)
    mosque = Column(String(128), nullable=False)
    bio = Column(Text, nullable=False)

    # Location & Map Coordinates
    latitude = Column(Float, nullable=True, default=35.6892)
    longitude = Column(Float, nullable=True, default=51.3890)
    address = Column(String(256), nullable=True)
    meeting_slots = Column(JSON, default=list)  # e.g. [{"day": "دوشنبه", "time": "۱۶:۰۰ الی ۱۸:۰۰", "location": "مسجد جامع", "capacity": 5}]

    user = relationship("User", back_populates="scholar_profile")
    threads = relationship("ConsultationThread", back_populates="target_scholar")
    quick_replies = relationship("ScholarQuickReply", back_populates="scholar", cascade="all, delete-orphan")
    meetings = relationship("ScholarMeeting", back_populates="scholar", cascade="all, delete-orphan")
    posts = relationship("ScholarPost", back_populates="scholar", cascade="all, delete-orphan")


class ScholarPost(Base):
    __tablename__ = "scholar_posts"

    id = Column(String(64), primary_key=True, index=True)
    scholar_id = Column(String(64), ForeignKey("scholars.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String(32), default="ARTICLE")  # ARTICLE, AUDIO, FATWA, ANNOUNCEMENT
    audio_url = Column(String(512), nullable=True)
    audio_duration_seconds = Column(Integer, nullable=True)
    tags = Column(JSON, default=list)
    book_reference = Column(JSON, nullable=True)
    likes_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scholar = relationship("Scholar", back_populates="posts")


class ScholarMeeting(Base):
    __tablename__ = "scholar_meetings"
    __table_args__ = (
        Index("ix_scholar_meetings_scholar_date", "scholar_id", "meeting_date"),
        Index("ix_scholar_meetings_user_date", "user_id", "meeting_date"),
    )

    id = Column(String(64), primary_key=True, index=True)
    scholar_id = Column(String(64), ForeignKey("scholars.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name = Column(String(128), nullable=False)
    user_phone = Column(String(32), nullable=False)
    meeting_date = Column(String(32), nullable=False)
    time_slot = Column(String(64), nullable=False)
    location = Column(String(256), nullable=True)
    subject = Column(String(256), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING")  # PENDING, CONFIRMED, CANCELLED, COMPLETED
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scholar = relationship("Scholar", back_populates="meetings")
