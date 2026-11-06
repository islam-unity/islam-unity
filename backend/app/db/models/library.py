from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class LibraryPoster(Base):
    __tablename__ = "library_posters"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(256), nullable=False)
    subtitle = Column(String(256), nullable=True)
    image_url = Column(String(512), nullable=False)
    target_book_id = Column(String(64), nullable=True)
    order_index = Column(Integer, default=0)


class LibraryCategory(Base):
    __tablename__ = "library_categories"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    icon_name = Column(String(64), default="menu_book")
    order_index = Column(Integer, default=0)
    parent_id = Column(String(64), ForeignKey("library_categories.id", ondelete="SET NULL"), nullable=True)

    parent = relationship("LibraryCategory", remote_side=[id], backref="subcategories")
    books = relationship("Book", back_populates="category")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        Index("ix_books_category_featured", "category_id", "is_featured"),
        Index("ix_books_title_author", "title", "author"),
    )

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(256), nullable=False, index=True)
    author = Column(String(128), nullable=False, index=True)
    translator = Column(String(128), nullable=True)
    publisher = Column(String(128), nullable=True)
    publication_year = Column(String(32), nullable=True)
    cover_url = Column(String(512), nullable=True)
    category_id = Column(String(64), ForeignKey("library_categories.id", ondelete="SET NULL"), nullable=True)
    is_featured = Column(Boolean, default=False)
    tags = Column(JSON, default=list)  # List of string tags
    topics = Column(JSON, default=list)  # List of domain/theological themes for SQL & RAG
    description = Column(Text, nullable=True)
    language = Column(String(16), default="fa", nullable=False)
    page_count = Column(Integer, default=100)
    rating = Column(Float, default=4.8)

    category = relationship("LibraryCategory", back_populates="books")
    chapters = relationship("BookChapter", back_populates="book", cascade="all, delete-orphan", order_by="BookChapter.chapter_number")
    highlights = relationship("BookHighlight", back_populates="book", cascade="all, delete-orphan")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="book", cascade="all, delete-orphan")
    reviews = relationship("BookReview", back_populates="book", cascade="all, delete-orphan")


class BookChapter(Base):
    __tablename__ = "book_chapters"
    __table_args__ = (
        Index("ix_book_chapters_book_number", "book_id", "chapter_number"),
    )

    id = Column(String(64), primary_key=True, index=True)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(256), nullable=False)
    reading_time_minutes = Column(Integer, default=5)
    content = Column(Text, nullable=False)
    paragraphs = Column(JSON, default=list)  # List of strings

    book = relationship("Book", back_populates="chapters")
    knowledge_chunks = relationship("KnowledgeChunk", back_populates="chapter", cascade="all, delete-orphan", order_by="KnowledgeChunk.chunk_order")


class UserShelf(Base):
    __tablename__ = "user_shelves"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(128), nullable=False)
    color_hex = Column(String(32), default="#4CAF50")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="shelves")
    shelf_items = relationship("ShelfBook", back_populates="shelf", cascade="all, delete-orphan")


class ShelfBook(Base):
    __tablename__ = "shelf_books"
    __table_args__ = (
        Index("ix_shelf_books_shelf_book", "shelf_id", "book_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    shelf_id = Column(String(64), ForeignKey("user_shelves.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    added_at = Column(DateTime, default=utc_now)

    shelf = relationship("UserShelf", back_populates="shelf_items")
    book = relationship("Book")


class BookHighlight(Base):
    __tablename__ = "book_highlights"
    __table_args__ = (
        Index("ix_book_highlights_user_book", "user_id", "book_id"),
    )

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(String(64), nullable=True)
    selected_text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    color_hex = Column(String(32), default="#FFE082")
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="highlights")
    book = relationship("Book", back_populates="highlights")


class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    __table_args__ = (
        Index("ix_reading_progress_user_book", "user_id", "book_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    current_chapter_id = Column(String(64), nullable=True)
    current_paragraph_index = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="reading_progress")
    book = relationship("Book")


class BookFavorite(Base):
    __tablename__ = "book_favorites"
    __table_args__ = (
        Index("ix_book_favorites_user_book", "user_id", "book_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utc_now)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("ix_chunks_book_chapter_order", "book_id", "chapter_id", "chunk_order"),
        Index("ix_chunks_book_order", "book_id", "chunk_order"),
        Index("ix_chunks_content_type", "content_type"),
    )

    id = Column(String(64), primary_key=True, index=True)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(String(64), ForeignKey("book_chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_order = Column(Integer, default=0)

    # Main texts
    full_text = Column(Text, nullable=False)
    text_arabic = Column(Text, nullable=True)

    # Compact representation for Jev (~30-50 words)
    summary = Column(Text, nullable=False)

    # Multi-vector analytical fields
    hypothetical_questions = Column(JSON, default=list)  # 3-5 synthetic questions
    core_concepts = Column(JSON, default=list)           # key concepts/keywords
    domain_insights = Column(JSON, default=list)         # morals / rulings / takeaways

    # Metadata & navigation
    page_number = Column(Integer, nullable=True)
    content_type = Column(String(32), default="TEXT")     # HADITH, FIQH, TAFSIR, ETHICS
    language = Column(String(16), default="fa", nullable=False)
    is_processed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

    book = relationship("Book", back_populates="knowledge_chunks")
    chapter = relationship("BookChapter", back_populates="knowledge_chunks")


class ReferenceTranslationCache(Base):
    __tablename__ = "reference_translation_cache"
    __table_args__ = (
        Index("ix_ref_trans_source_target", "source_id", "target_language"),
    )

    id = Column(String(64), primary_key=True, index=True)
    source_id = Column(String(256), index=True, nullable=False)
    source_type = Column(String(32), default="CHUNK", nullable=False)  # CHUNK, BOOK, QURAN, HADITH
    target_language = Column(String(16), index=True, nullable=False)   # fa, ar, en, ur, ...
    translated_title = Column(String(512), nullable=True)
    translated_excerpt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class RAGEvaluationReport(Base):
    __tablename__ = "rag_evaluation_reports"

    id = Column(String(64), primary_key=True, index=True)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(256), nullable=False)
    total_queries = Column(Integer, default=0, nullable=False)
    avg_relevance_score = Column(Float, default=0.0, nullable=False)
    hit_rate_at_3 = Column(Float, default=0.0, nullable=False)
    passing_rate = Column(Float, default=0.0, nullable=False)
    status = Column(String(32), default="COMPLETED")  # PASSED, NEEDS_IMPROVEMENT, FAILED
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now)

    book = relationship("Book")


class BookSubmissionRequest(Base):
    __tablename__ = "book_submissions"

    id = Column(String(64), primary_key=True, index=True)
    type = Column(String(32), nullable=False, default="SUBMIT_NEW")  # SUBMIT_NEW or REQUEST_EXISTING
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name = Column(String(128), nullable=True)
    user_contact = Column(String(128), nullable=True)  # Phone or email
    title = Column(String(256), nullable=False, index=True)
    author = Column(String(128), nullable=True)
    translator = Column(String(128), nullable=True)
    publisher = Column(String(128), nullable=True)
    category = Column(String(128), nullable=True)
    isbn = Column(String(64), nullable=True)
    file_url = Column(String(512), nullable=True)
    cover_url = Column(String(512), nullable=True)
    submission_type = Column(String(64), default="FREE")  # WAQF_FREE, OPEN_ACCESS, REVIEW, GENERAL
    description = Column(Text, nullable=True)
    tracking_code = Column(String(32), unique=True, index=True, nullable=False)
    status = Column(String(32), default="PENDING", index=True)  # PENDING, IN_REVIEW, APPROVED, AVAILABLE, REJECTED
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", foreign_keys=[user_id])


class BookReview(Base):
    __tablename__ = "book_reviews"
    __table_args__ = (
        Index("ix_book_reviews_book_approved", "book_id", "is_approved"),
    )

    id = Column(String(64), primary_key=True, index=True)
    book_id = Column(String(64), ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    author_name = Column(String(128), nullable=False)
    avatar_url = Column(String(512), nullable=True)
    rating = Column(Float, default=5.0)
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=utc_now)

    book = relationship("Book", back_populates="reviews")
    user = relationship("User", foreign_keys=[user_id])



