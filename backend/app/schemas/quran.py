from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DailyVerseDTO(BaseModel):
    surahId: int
    surahName: str
    ayahNumber: int
    textArabic: str
    textPersian: str
    theme: str
    juz: int
    page: int


class SurahListItemDTO(BaseModel):
    id: int
    nameArabic: str
    namePersian: str
    nameTransliterated: str
    ayahCount: int
    revelationType: str
    juzNumber: int
    revelationOrder: int
    startPage: int
    endPage: int
    summary: str


class AyahDTO(BaseModel):
    surahId: int
    ayahNumber: int
    textArabic: str
    textPersian: str
    juz: int
    hizb: int
    page: int
    sajdah: bool
    isBookmarked: bool = False


class SurahAyahsData(BaseModel):
    surah: Dict[str, Any]
    ayahs: List[AyahDTO]


class MushafPageData(BaseModel):
    pageNumber: int
    juz: int
    hizb: int
    ayahs: List[AyahDTO]


class KeywordItem(BaseModel):
    word: str
    meaning: str


class RelatedAyahItem(BaseModel):
    surahId: int
    ayahNumber: int
    relation: str


class AyahToolsDTO(BaseModel):
    surahId: int
    surahName: str
    ayahNumber: int
    textArabic: str
    textPersian: str
    translations: Dict[str, str]
    briefTafsir: str
    keywords: List[KeywordItem]
    aiTadabbur: List[str]
    reflectionQuestion: str
    relatedAyahs: List[RelatedAyahItem]


class ReciterDTO(BaseModel):
    id: str
    nameFa: str
    nameAr: str
    style: str
    bitrate: str
    isDefault: bool


class AudioSegmentItem(BaseModel):
    ayahNumber: int
    startMs: int
    endMs: int


class SurahAudioResponse(BaseModel):
    surahId: int
    reciterId: str
    audioUrl: str
    durationMs: int
    segments: List[AudioSegmentItem]


class BookmarkToggleRequest(BaseModel):
    surahId: int
    ayahNumber: int


class BookmarkToggleResponse(BaseModel):
    isBookmarked: bool
    bookmarkId: Optional[str] = None


class LastReadSyncRequest(BaseModel):
    surahId: int
    ayahNumber: int
    pageNumber: int
    timestamp: int


class QuranSearchItemDTO(BaseModel):
    surahId: int
    surahName: str
    ayahNumber: int
    textArabic: str
    textPersian: str
    page: int
    matchScope: str


class ThematicSurahGenerateRequest(BaseModel):
    topic: str
    reciterId: Optional[str] = "parhizgar"


class ThematicAyahDTO(BaseModel):
    id: Optional[int] = None
    orderIndex: int
    originalSurahId: int
    originalSurahName: str
    originalAyahNumber: int
    textArabic: str
    textPersian: str
    tafsirLesson: str
    reflectionQuestion: Optional[str] = None
    jevScore: int = 8
    audioUrl: Optional[str] = None


class ThematicSurahDetailDTO(BaseModel):
    id: str
    title: str
    topic: str
    summary: str
    isFeatured: bool
    searchCount: int
    ayahCount: int
    ayahs: List[ThematicAyahDTO]
    createdAt: str


class ThematicSurahListItemDTO(BaseModel):
    id: str
    title: str
    topic: str
    summary: str
    isFeatured: bool
    searchCount: int
    ayahCount: int


class ThematicSurahUpdateRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    isFeatured: Optional[bool] = None


class SingleAyahDTO(BaseModel):
    surahId: int
    surahName: str
    ayahNumber: int
    globalNumber: Optional[int] = None
    textArabic: str
    textClean: str
    textPersian: str
    translations: Dict[str, str] = {}
    juz: int
    hizb: int
    page: int
    sajdah: bool


class QuranDownloadAyahDTO(BaseModel):
    ayahNumber: int
    globalNumber: Optional[int] = None
    textArabic: str
    textClean: str
    textPersian: str
    translations: Optional[Dict[str, str]] = None
    juz: int
    hizb: int
    page: int
    sajdah: bool


class QuranDownloadSurahDTO(BaseModel):
    id: int
    nameArabic: str
    namePersian: str
    nameTransliterated: str
    ayahCount: int
    revelationType: str
    juzNumber: int
    revelationOrder: int
    startPage: int
    endPage: int
    summary: str
    ayahs: List[QuranDownloadAyahDTO]


class QuranDownloadResponse(BaseModel):
    info: Dict[str, Any]
    surahs: List[QuranDownloadSurahDTO]


