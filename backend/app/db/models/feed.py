from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_status_created", "status", "created_at"),
        Index("ix_posts_author_status", "user_id", "status"),
        Index("ix_posts_scholar_status", "scholar_id", "status"),
        Index("ix_posts_category_status", "category", "status"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scholar_id = Column(String(64), ForeignKey("scholars.id", ondelete="SET NULL"), nullable=True, index=True)
    is_scholar_post = Column(Boolean, default=False, index=True)

    # Content fields
    title = Column(String(256), nullable=True)
    content = Column(Text, nullable=False)  # Caption / text body
    content_type = Column(String(32), default="MULTIMEDIA")  # MULTIMEDIA, VIDEO, AUDIO, IMAGE_GALLERY, IMAGE_SINGLE, TEXT
    category = Column(String(64), default="GENERAL", index=True)  # FIQH, AKHLAQ, TAFSIR, AQAED, FAMILY, LIFESTYLE, GENERAL
    madhhab = Column(String(64), default="مشترک", index=True)  # مشترک, شیعه اثناعشری, اهل سنت حنفی, اهل سنت شافعی

    # Religious references & tags
    quran_references = Column(JSON, default=list)  # [{"surah": "...", "ayah": 186, "text": "..."}]
    hadith_references = Column(JSON, default=list)  # [{"source": "...", "text": "..."}]
    tags = Column(JSON, default=list)  # ["#نماز", "#آرامش", "#تقریب"]

    # Moderation & Lifecycle
    status = Column(String(32), default="PUBLISHED", index=True)  # PUBLISHED, PENDING_REVIEW, REPORTED_HIDDEN, ARCHIVED
    moderation_note = Column(String(256), nullable=True)

    # Social statistics
    views_count = Column(Integer, default=0)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)

    # Pinned comment id (e.g. pinned scholar fatwa / answer)
    pinned_comment_id = Column(String(64), nullable=True)

    # Cached AI summary & insights
    ai_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    author = relationship("User", foreign_keys=[user_id])
    scholar = relationship("Scholar", foreign_keys=[scholar_id])
    media_items = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan", order_by="PostMedia.order")
    comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan", order_by="desc(PostComment.created_at)")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")
    bookmarks = relationship("PostBookmark", back_populates="post", cascade="all, delete-orphan")
    reports = relationship("PostReport", back_populates="post", cascade="all, delete-orphan")


class PostMedia(Base):
    __tablename__ = "post_media"
    __table_args__ = (
        Index("ix_post_media_post_order", "post_id", "order"),
    )

    id = Column(String(64), primary_key=True, index=True)
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    media_type = Column(String(32), nullable=False)  # IMAGE, VIDEO, AUDIO
    media_url = Column(String(512), nullable=False)
    thumbnail_url = Column(String(512), nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # for video and audio
    file_size_bytes = Column(Integer, nullable=True)
    aspect_ratio = Column(String(16), default="1:1")  # 1:1, 9:16, 16:9, 4:5
    order = Column(Integer, default=0)

    post = relationship("Post", back_populates="media_items")


class PostComment(Base):
    __tablename__ = "post_comments"
    __table_args__ = (
        Index("ix_post_comments_post_created", "post_id", "created_at"),
    )

    id = Column(String(64), primary_key=True, index=True)
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(String(64), ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True, index=True)

    content = Column(Text, nullable=False)
    is_scholar_reply = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    status = Column(String(32), default="APPROVED")  # APPROVED, FILTERED, REPORTED

    created_at = Column(DateTime, default=utc_now, index=True)

    post = relationship("Post", back_populates="comments")
    user = relationship("User")
    parent = relationship("PostComment", remote_side=[id], back_populates="replies")
    replies = relationship("PostComment", back_populates="parent", cascade="all, delete-orphan", order_by="PostComment.created_at")
    comment_likes = relationship("PostCommentLike", back_populates="comment", cascade="all, delete-orphan")


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_user_like"),
    )

    post = relationship("Post", back_populates="likes")
    user = relationship("User")


class PostBookmark(Base):
    __tablename__ = "post_bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_post_user_bookmark"),
    )

    post = relationship("Post", back_populates="bookmarks")
    user = relationship("User")


class PostCommentLike(Base):
    __tablename__ = "post_comment_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(String(64), ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("comment_id", "user_id", name="uq_comment_user_like"),
    )

    comment = relationship("PostComment", back_populates="comment_likes")
    user = relationship("User")


class PostReport(Base):
    __tablename__ = "post_reports"

    id = Column(String(64), primary_key=True, index=True)
    post_id = Column(String(64), ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reason = Column(String(128), nullable=False)  # INAPPROPRIATE, MISINFORMATION, SECTARIAN_STRIFE, SPAM, OTHER
    description = Column(Text, nullable=True)
    status = Column(String(32), default="PENDING")  # PENDING, RESOLVED_DISMISSED, RESOLVED_REMOVED
    created_at = Column(DateTime, default=utc_now)

    post = relationship("Post", back_populates="reports")
    user = relationship("User")
