from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class ConsultationThread(Base):
    __tablename__ = "consultation_threads"
    __table_args__ = (
        Index("ix_threads_user_status", "user_id", "status"),
        Index("ix_threads_scholar_status", "target_scholar_id", "status"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    target_scholar_id = Column(String(64), ForeignKey("scholars.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(256), nullable=False, index=True)
    category = Column(String(128), nullable=False, index=True)
    tracking_code = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(32), default="WAITING_SCHOLAR", nullable=False)  # WAITING_SCHOLAR, OPEN, CLOSED, ANSWERED
    is_anonymous = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    is_urgent = Column(Boolean, default=False)
    is_bookmarked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="threads")
    target_scholar = relationship("Scholar", back_populates="threads")
    messages = relationship("ConsultationMessage", back_populates="thread", cascade="all, delete-orphan", order_by="ConsultationMessage.created_at")
    attachments = relationship("ConsultationAttachment", back_populates="thread", cascade="all, delete-orphan")


class ConsultationMessage(Base):
    __tablename__ = "consultation_messages"
    __table_args__ = (
        Index("ix_consult_messages_thread_created", "thread_id", "created_at"),
    )

    id = Column(String(64), primary_key=True, index=True)
    thread_id = Column(String(64), ForeignKey("consultation_threads.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_role = Column(String(32), nullable=False)  # SEEKER, SCHOLAR
    text = Column(Text, nullable=False)
    citation = Column(Text, nullable=True)
    book_reference = Column(JSON, nullable=True)  # Structured book/passage citation for deep linking to reader
    attachment_id = Column(String(64), ForeignKey("consultation_attachments.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    thread = relationship("ConsultationThread", back_populates="messages")
    attachment = relationship("ConsultationAttachment", foreign_keys=[attachment_id])


class ConsultationAttachment(Base):
    __tablename__ = "consultation_attachments"

    id = Column(String(64), primary_key=True, index=True)
    thread_id = Column(String(64), ForeignKey("consultation_threads.id", ondelete="CASCADE"), nullable=True)
    uploader_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(32), nullable=False)  # VOICE, VIDEO, IMAGE, DOCUMENT
    title = Column(String(256), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    file_url = Column(String(512), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    thread = relationship("ConsultationThread", back_populates="attachments")


class ScholarQuickReply(Base):
    __tablename__ = "scholar_quick_replies"

    id = Column(String(64), primary_key=True, index=True)
    scholar_id = Column(String(64), ForeignKey("scholars.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(64), default="عمومی")  # احوالپرسی، اعلام بررسی، ارجاع، نصیحت اخلاقی

    scholar = relationship("Scholar", back_populates="quick_replies")
