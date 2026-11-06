from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, utc_now


class Surah(Base):
    __tablename__ = "quran_surahs"

    id = Column(Integer, primary_key=True)  # 1 to 114
    name_arabic = Column(String(64), nullable=False, index=True)
    name_persian = Column(String(64), nullable=False, index=True)
    name_transliterated = Column(String(64), nullable=False, index=True)
    ayah_count = Column(Integer, nullable=False)
    revelation_type = Column(String(16), nullable=False)  # MAKKI, MADANI
    juz_number = Column(Integer, nullable=False)
    revelation_order = Column(Integer, nullable=False)
    start_page = Column(Integer, nullable=False)
    end_page = Column(Integer, nullable=False)
    summary = Column(Text, nullable=False)

    ayahs = relationship("Ayah", back_populates="surah", cascade="all, delete-orphan", order_by="Ayah.ayah_number")


class Ayah(Base):
    __tablename__ = "quran_ayahs"
    __table_args__ = (
        Index("ix_quran_ayahs_surah_ayah", "surah_id", "ayah_number"),
        Index("ix_quran_ayahs_juz_page", "juz", "page"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    surah_id = Column(Integer, ForeignKey("quran_surahs.id", ondelete="CASCADE"), nullable=False, index=True)
    ayah_number = Column(Integer, nullable=False, index=True)
    text_arabic = Column(Text, nullable=False)
    text_persian = Column(Text, nullable=False)
    text_clean = Column(Text, nullable=False, index=True)  # without tashkeel for fast search
    juz = Column(Integer, nullable=False, index=True)
    hizb = Column(Integer, nullable=False)
    page = Column(Integer, nullable=False, index=True)
    sajdah = Column(Boolean, default=False)

    surah = relationship("Surah", back_populates="ayahs")


class AyahTadabburData(Base):
    __tablename__ = "quran_ayah_tadabbur"
    __table_args__ = (
        Index("ix_tadabbur_surah_ayah", "surah_id", "ayah_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    surah_id = Column(Integer, nullable=False, index=True)
    ayah_number = Column(Integer, nullable=False, index=True)
    brief_tafsir = Column(Text, nullable=False)
    keywords = Column(JSON, default=list)  # [{"word": "...", "meaning": "..."}]
    ai_tadabbur = Column(JSON, default=list)  # list of string insights
    reflection_question = Column(Text, nullable=False)
    related_ayahs = Column(JSON, default=list)  # [{"surahId": ..., "ayahNumber": ..., "relation": "..."}]
    translations = Column(JSON, default=dict)  # {"ansarian": "...", "makarem": "...", "fooladvand": "..."}


class Reciter(Base):
    __tablename__ = "quran_reciters"

    id = Column(String(64), primary_key=True)  # parhizgar, abdulbasit, menshawi, hussary
    name_fa = Column(String(128), nullable=False)
    name_ar = Column(String(128), nullable=False)
    style = Column(String(128), nullable=False)
    bitrate = Column(String(32), default="128kbps")
    is_default = Column(Boolean, default=False)


class AudioSegment(Base):
    __tablename__ = "quran_audio_segments"
    __table_args__ = (
        Index("ix_audio_segments_reciter_surah", "reciter_id", "surah_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    surah_id = Column(Integer, nullable=False, index=True)
    reciter_id = Column(String(64), ForeignKey("quran_reciters.id"), nullable=False, index=True)
    audio_url = Column(String(512), nullable=False)
    duration_ms = Column(Integer, nullable=False)
    segments = Column(JSON, default=list)  # [{"ayahNumber": 1, "startMs": 0, "endMs": 5200}]


class QuranBookmark(Base):
    __tablename__ = "quran_bookmarks"
    __table_args__ = (
        Index("ix_quran_bookmarks_user_surah", "user_id", "surah_id", "ayah_number"),
    )

    id = Column(String(64), primary_key=True)  # bm_49_10
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    surah_id = Column(Integer, nullable=False)
    ayah_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="bookmarks")


class LastReadPosition(Base):
    __tablename__ = "quran_last_read"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    surah_id = Column(Integer, nullable=False)
    ayah_number = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    timestamp = Column(Integer, nullable=False)  # epoch ms


class ThematicSurah(Base):
    __tablename__ = "quran_thematic_surahs"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(256), nullable=False, index=True)
    topic = Column(String(256), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    is_featured = Column(Boolean, default=False, index=True)
    search_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    ayahs = relationship("ThematicAyah", back_populates="thematic_surah", cascade="all, delete-orphan", order_by="ThematicAyah.order_index")


class ThematicAyah(Base):
    __tablename__ = "quran_thematic_ayahs"
    __table_args__ = (
        Index("ix_thematic_ayahs_surah_order", "thematic_surah_id", "order_index"),
        Index("ix_thematic_ayahs_orig_ref", "original_surah_id", "original_ayah_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    thematic_surah_id = Column(String(64), ForeignKey("quran_thematic_surahs.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, index=True)
    original_surah_id = Column(Integer, nullable=False)
    original_surah_name = Column(String(64), nullable=False)
    original_ayah_number = Column(Integer, nullable=False)
    text_arabic = Column(Text, nullable=False)
    text_persian = Column(Text, nullable=False)
    tafsir_lesson = Column(Text, nullable=False)
    reflection_question = Column(Text, nullable=True)
    jev_score = Column(Integer, default=8)
    audio_url = Column(String(512), nullable=True)

    thematic_surah = relationship("ThematicSurah", back_populates="ayahs")

