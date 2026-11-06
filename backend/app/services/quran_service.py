import json
import uuid
import re
import os
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc, asc, func
from sqlalchemy.orm import selectinload

from app.db.models import (
    Surah, Ayah, AyahTadabburData, Reciter,
    AudioSegment, QuranBookmark, LastReadPosition,
    ThematicSurah, ThematicAyah
)
from app.schemas.quran import (
    DailyVerseDTO, SurahListItemDTO, AyahDTO, SurahAyahsData,
    MushafPageData, AyahToolsDTO, KeywordItem, RelatedAyahItem,
    ReciterDTO, AudioSegmentItem, SurahAudioResponse,
    BookmarkToggleResponse, QuranSearchItemDTO,
    ThematicSurahGenerateRequest, ThematicAyahDTO,
    ThematicSurahDetailDTO, ThematicSurahListItemDTO,
    ThematicSurahUpdateRequest, SingleAyahDTO
)
from app.core.exceptions import SurahNotFoundException, AyahNotFoundException, AppException
from app.services.jev_service import JevService
from app.services.llm_provider_service import LLMProviderService


class QuranService:
    @staticmethod
    async def get_daily_verse(db: AsyncSession) -> DailyVerseDTO:
        # Fetch Surah 49 Ayah 10 as golden default daily verse or fallback to 1:1
        stmt = select(Ayah).where(Ayah.surah_id == 49, Ayah.ayah_number == 10)
        ayah = await db.scalar(stmt)
        if not ayah:
            ayah = await db.scalar(select(Ayah).where(Ayah.surah_id == 1, Ayah.ayah_number == 1))

        surah = await db.scalar(select(Surah).where(Surah.id == (ayah.surah_id if ayah else 1)))

        return DailyVerseDTO(
            surahId=ayah.surah_id if ayah else 49,
            surahName=surah.name_arabic if surah else "الحجرات",
            ayahNumber=ayah.ayah_number if ayah else 10,
            textArabic=ayah.text_arabic if ayah else "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ ۚ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ",
            textPersian=ayah.text_persian if ayah else "همانا مؤمنان برادر یکدیگرند؛ پس میان دو برادر خود صلح و آشتی برقرار سازید و تقوای الهی پیشه کنید، باشد که مورد رحمت قرار گیرید.",
            theme="پیوند برادری ایمانی و اصلاح ذات‌البین",
            juz=ayah.juz if ayah else 26,
            page=ayah.page if ayah else 516
        )

    @staticmethod
    async def get_surahs(
        db: AsyncSession,
        q: Optional[str] = None,
        revelation_type: Optional[str] = None,
        juz: Optional[int] = None,
        sort: Optional[str] = "MUSHAF"
    ) -> List[SurahListItemDTO]:
        stmt = select(Surah)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(
                Surah.name_arabic.ilike(pattern),
                Surah.name_persian.ilike(pattern),
                Surah.name_transliterated.ilike(pattern)
            ))
        if revelation_type:
            stmt = stmt.where(Surah.revelation_type == revelation_type)
        if juz:
            stmt = stmt.where(Surah.juz_number == juz)

        if sort == "REVELATION":
            stmt = stmt.order_by(asc(Surah.revelation_order))
        elif sort == "AYAH_COUNT_DESC":
            stmt = stmt.order_by(desc(Surah.ayah_count))
        elif sort == "AYAH_COUNT_ASC":
            stmt = stmt.order_by(asc(Surah.ayah_count))
        else:  # MUSHAF
            stmt = stmt.order_by(asc(Surah.id))

        res = await db.execute(stmt)
        surahs = res.scalars().all()
        return [
            SurahListItemDTO(
                id=s.id,
                nameArabic=s.name_arabic,
                namePersian=s.name_persian,
                nameTransliterated=s.name_transliterated,
                ayahCount=s.ayah_count,
                revelationType=s.revelation_type,
                juzNumber=s.juz_number,
                revelationOrder=s.revelation_order,
                startPage=s.start_page,
                endPage=s.end_page,
                summary=s.summary
            ) for s in surahs
        ]

    @staticmethod
    async def get_surah_detail(db: AsyncSession, surah_id: int) -> SurahListItemDTO:
        surah = await db.scalar(select(Surah).where(Surah.id == surah_id))
        if not surah:
            raise SurahNotFoundException()
        return SurahListItemDTO(
            id=surah.id,
            nameArabic=surah.name_arabic,
            namePersian=surah.name_persian,
            nameTransliterated=surah.name_transliterated,
            ayahCount=surah.ayah_count,
            revelationType=surah.revelation_type,
            juzNumber=surah.juz_number,
            revelationOrder=surah.revelation_order,
            startPage=surah.start_page,
            endPage=surah.end_page,
            summary=surah.summary
        )

    @staticmethod
    async def get_surah_ayahs(
        db: AsyncSession,
        surah_id: int,
        translation: str = "ansarian",
        page: Optional[int] = None,
        limit: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> SurahAyahsData:
        surah = await db.scalar(select(Surah).where(Surah.id == surah_id))
        if not surah:
            raise SurahNotFoundException()

        stmt = select(Ayah).where(Ayah.surah_id == surah_id).order_by(asc(Ayah.ayah_number))
        if page and limit:
            offset = (page - 1) * limit
            stmt = stmt.offset(offset).limit(limit)

        res = await db.execute(stmt)
        ayahs = res.scalars().all()

        # If non-default translation requested, fetch from tadabbur translations store
        translation_map = {}
        if translation != "ansarian":
            t_res = await db.execute(
                select(AyahTadabburData.ayah_number, AyahTadabburData.translations).where(
                    AyahTadabburData.surah_id == surah_id
                )
            )
            for row in t_res.all():
                t_dict = row[1] or {}
                if translation in t_dict:
                    translation_map[row[0]] = t_dict[translation]

        # User bookmarks set for fast lookup
        bookmarked_set = set()
        if user_id:
            bm_res = await db.execute(select(QuranBookmark.ayah_number).where(
                QuranBookmark.user_id == user_id,
                QuranBookmark.surah_id == surah_id
            ))
            bookmarked_set = set(bm_res.scalars().all())

        ayah_dtos = [
            AyahDTO(
                surahId=a.surah_id,
                ayahNumber=a.ayah_number,
                textArabic=a.text_arabic,
                textPersian=translation_map.get(a.ayah_number, a.text_persian),
                juz=a.juz,
                hizb=a.hizb,
                page=a.page,
                sajdah=a.sajdah,
                isBookmarked=a.ayah_number in bookmarked_set
            ) for a in ayahs
        ]

        return SurahAyahsData(
            surah={
                "id": surah.id,
                "nameArabic": surah.name_arabic,
                "namePersian": surah.name_persian,
                "ayahCount": surah.ayah_count
            },
            ayahs=ayah_dtos
        )

    @staticmethod
    async def get_ayah(
        db: AsyncSession,
        surah_id: int,
        ayah_number: int,
        translation: str = "ansarian"
    ) -> SingleAyahDTO:
        surah = await db.scalar(select(Surah).where(Surah.id == surah_id))
        ayah = await db.scalar(select(Ayah).where(Ayah.surah_id == surah_id, Ayah.ayah_number == ayah_number))
        if not ayah:
            raise AyahNotFoundException()

        tadabbur = await db.scalar(select(AyahTadabburData).where(
            AyahTadabburData.surah_id == surah_id,
            AyahTadabburData.ayah_number == ayah_number
        ))
        translations = (tadabbur.translations if tadabbur else {}) or {}
        pe_text = translations.get(translation, ayah.text_persian)

        return SingleAyahDTO(
            surahId=ayah.surah_id,
            surahName=surah.name_arabic if surah else f"سوره {surah_id}",
            ayahNumber=ayah.ayah_number,
            globalNumber=None,
            textArabic=ayah.text_arabic,
            textClean=ayah.text_clean,
            textPersian=pe_text,
            translations=translations,
            juz=ayah.juz,
            hizb=ayah.hizb,
            page=ayah.page,
            sajdah=ayah.sajdah
        )

    @staticmethod
    async def get_quran_download_data(
        db: AsyncSession,
        surah_id: Optional[int] = None,
        translation: str = "ansarian"
    ) -> Dict[str, Any]:
        data_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "quran_complete.json")
        if os.path.exists(data_file):
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    full_data = json.load(f)

                if surah_id is not None:
                    matched = [s for s in full_data.get("surahs", []) if s.get("id") == surah_id]
                    if not matched:
                        raise SurahNotFoundException()
                    return {
                        "info": {
                            **full_data.get("info", {}),
                            "filterSurahId": surah_id
                        },
                        "surahs": matched
                    }
                return full_data
            except AppException:
                raise
            except Exception:
                pass

        # Fallback to database queries
        stmt = select(Surah).order_by(asc(Surah.id))
        if surah_id is not None:
            stmt = stmt.where(Surah.id == surah_id)
        s_res = await db.execute(stmt)
        surahs = s_res.scalars().all()
        if surah_id is not None and not surahs:
            raise SurahNotFoundException()

        out_surahs = []
        for s in surahs:
            a_stmt = select(Ayah).where(Ayah.surah_id == s.id).order_by(asc(Ayah.ayah_number))
            a_res = await db.execute(a_stmt)
            ayahs = a_res.scalars().all()

            ayah_list = [
                {
                    "ayahNumber": a.ayah_number,
                    "textArabic": a.text_arabic,
                    "textClean": a.text_clean,
                    "textPersian": a.text_persian,
                    "juz": a.juz,
                    "hizb": a.hizb,
                    "page": a.page,
                    "sajdah": a.sajdah
                }
                for a in ayahs
            ]
            out_surahs.append({
                "id": s.id,
                "nameArabic": s.name_arabic,
                "namePersian": s.name_persian,
                "nameTransliterated": s.name_transliterated,
                "ayahCount": s.ayah_count,
                "revelationType": s.revelation_type,
                "revelationOrder": s.revelation_order,
                "juzNumber": s.juz_number,
                "startPage": s.start_page,
                "endPage": s.end_page,
                "summary": s.summary,
                "ayahs": ayah_list
            })

        return {
            "info": {
                "name": "القرآن الكريم",
                "description": "متن کامل ۱۱۴ سوره و ۶۲۳۶ آیه قرآن کریم",
                "totalSurahs": len(out_surahs),
                "totalAyahs": sum(len(s["ayahs"]) for s in out_surahs)
            },
            "surahs": out_surahs
        }


    @staticmethod
    async def get_mushaf_page(db: AsyncSession, page_number: int, user_id: Optional[str] = None) -> MushafPageData:
        stmt = select(Ayah).where(Ayah.page == page_number).order_by(asc(Ayah.surah_id), asc(Ayah.ayah_number))
        res = await db.execute(stmt)
        ayahs = res.scalars().all()

        if not ayahs:
            # Fallback to page 1
            stmt = select(Ayah).where(Ayah.page == 1).order_by(asc(Ayah.ayah_number))
            res = await db.execute(stmt)
            ayahs = res.scalars().all()

        bookmarked_set = set()
        if user_id:
            bm_res = await db.execute(select(QuranBookmark.ayah_number).where(QuranBookmark.user_id == user_id))
            bookmarked_set = set(bm_res.scalars().all())

        ayah_dtos = [
            AyahDTO(
                surahId=a.surah_id,
                ayahNumber=a.ayah_number,
                textArabic=a.text_arabic,
                textPersian=a.text_persian,
                juz=a.juz,
                hizb=a.hizb,
                page=a.page,
                sajdah=a.sajdah,
                isBookmarked=a.ayah_number in bookmarked_set
            ) for a in ayahs
        ]

        first_ayah = ayahs[0] if ayahs else None
        return MushafPageData(
            pageNumber=page_number,
            juz=first_ayah.juz if first_ayah else 1,
            hizb=first_ayah.hizb if first_ayah else 1,
            ayahs=ayah_dtos
        )

    @staticmethod
    async def get_ayah_tools(db: AsyncSession, surah_id: int, ayah_number: int) -> AyahToolsDTO:
        surah = await db.scalar(select(Surah).where(Surah.id == surah_id))
        surah_name = surah.name_arabic if surah else "الحجرات"

        ayah = await db.scalar(select(Ayah).where(Ayah.surah_id == surah_id, Ayah.ayah_number == ayah_number))
        tadabbur = await db.scalar(select(AyahTadabburData).where(
            AyahTadabburData.surah_id == surah_id,
            AyahTadabburData.ayah_number == ayah_number
        ))

        if not tadabbur:
            # Provide intelligent generic default if not specifically seeded
            text_ar = ayah.text_arabic if ayah else "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"
            text_fa = ayah.text_persian if ayah else "به نام خداوند بخشنده مهربان"
            return AyahToolsDTO(
                surahId=surah_id,
                surahName=surah_name,
                ayahNumber=ayah_number,
                textArabic=text_ar,
                textPersian=text_fa,
                translations={
                    "ansarian": text_fa,
                    "makarem": text_fa,
                    "fooladvand": text_fa
                },
                briefTafsir="این آیه شریفه متضمن هدایت‌های بنیادین توحیدی و اخلاقی در مسیر تکامل فرد و سلامت جامعه است.",
                keywords=[{"word": "الله", "meaning": "مبداء و غایت هستی و کمال مطلق"}],
                aiTadabbur=["هر کلمه از این آیه دریچه‌ای به سوی بیداری دل و اتصال به رحمت لایتناهی است."],
                reflectionQuestion="چگونه می‌توان این پیام الهی را در روابط روزمره متجلی ساخت؟",
                relatedAyahs=[{"surahId": 1, "ayahNumber": 1, "relation": "آغاز با نام و یاد پروردگار"}]
            )

        keywords = [KeywordItem(word=k["word"], meaning=k["meaning"]) for k in (tadabbur.keywords or [])]
        related = [RelatedAyahItem(surahId=r["surahId"], ayahNumber=r["ayahNumber"], relation=r["relation"]) for r in (tadabbur.related_ayahs or [])]

        return AyahToolsDTO(
            surahId=surah_id,
            surahName=surah_name,
            ayahNumber=ayah_number,
            textArabic=ayah.text_arabic if ayah else "",
            textPersian=ayah.text_persian if ayah else "",
            translations=tadabbur.translations or {},
            briefTafsir=tadabbur.brief_tafsir,
            keywords=keywords,
            aiTadabbur=tadabbur.ai_tadabbur or [],
            reflectionQuestion=tadabbur.reflection_question,
            relatedAyahs=related
        )

    @staticmethod
    async def get_reciters(db: AsyncSession) -> List[ReciterDTO]:
        res = await db.execute(select(Reciter))
        db_reciters = res.scalars().all()
        if db_reciters:
            return [
                ReciterDTO(
                    id=r.id,
                    nameFa=r.name_fa,
                    nameAr=r.name_ar,
                    style=r.style,
                    bitrate=r.bitrate,
                    isDefault=r.is_default
                ) for r in db_reciters
            ]
        # World-standard premier reciters CDN default
        return [
            ReciterDTO(
                id="parhizgar",
                nameFa="استاد شهریار پرهیزگار",
                nameAr="الشيخ شهريار برهيزكار",
                style="ترتیل آموزشی و روان",
                bitrate="128kbps",
                isDefault=True
            ),
            ReciterDTO(
                id="menshawi",
                nameFa="استاد محمد صدیق منشاوی",
                nameAr="الشيخ محمد صديق المنشاوي",
                style="ترتیل خاشعانه مصری",
                bitrate="128kbps",
                isDefault=False
            ),
            ReciterDTO(
                id="abdulbasit",
                nameFa="استاد عبدالباسط عبدالصمد",
                nameAr="الشيخ عبدالباسط عبدالصمد",
                style="تجوید و لحن ماندگار",
                bitrate="128kbps",
                isDefault=False
            ),
            ReciterDTO(
                id="alafasy",
                nameFa="شیخ مشاری راشد العفاسی",
                nameAr="الشيخ مشاري راشد العفاسي",
                style="ترتیل مدرن و محبوب",
                bitrate="128kbps",
                isDefault=False
            ),
            ReciterDTO(
                id="hussary",
                nameFa="شیخ محمود خلیل الحصری",
                nameAr="الشيخ محمود خليل الحصري",
                style="ترتیل فصیح و مخارج حروف",
                bitrate="128kbps",
                isDefault=False
            ),
            ReciterDTO(
                id="ghamadi",
                nameFa="شیخ سعد الغامدی",
                nameAr="الشيخ سعد الغامدي",
                style="ترتیل حزین و دلنشین",
                bitrate="128kbps",
                isDefault=False
            )
        ]

    @staticmethod
    async def get_surah_audio(db: AsyncSession, surah_id: int, reciter_id: str = "parhizgar") -> SurahAudioResponse:
        stmt = select(AudioSegment).where(
            AudioSegment.surah_id == surah_id,
            AudioSegment.reciter_id == reciter_id
        )
        audio = await db.scalar(stmt)

        WORLD_SURAH_AUDIO_URLS = {
            "parhizgar": f"https://server11.mp3quran.net/parhizgar/{surah_id:03d}.mp3",
            "menshawi": f"https://server10.mp3quran.net/minsh/{surah_id:03d}.mp3",
            "abdulbasit": f"https://server7.mp3quran.net/basit/{surah_id:03d}.mp3",
            "alafasy": f"https://server8.mp3quran.net/afs/{surah_id:03d}.mp3",
            "hussary": f"https://server13.mp3quran.net/husr/{surah_id:03d}.mp3",
            "ghamadi": f"https://server7.mp3quran.net/s_gmd/{surah_id:03d}.mp3",
        }
        live_cdn_url = WORLD_SURAH_AUDIO_URLS.get(reciter_id, f"https://server8.mp3quran.net/afs/{surah_id:03d}.mp3")

        if not audio:
            return SurahAudioResponse(
                surahId=surah_id,
                reciterId=reciter_id,
                audioUrl=live_cdn_url,
                durationMs=180000,
                segments=[
                    AudioSegmentItem(ayahNumber=1, startMs=0, endMs=10000)
                ]
            )

        seg_items = [
            AudioSegmentItem(
                ayahNumber=s["ayahNumber"],
                startMs=s["startMs"],
                endMs=s["endMs"]
            ) for s in (audio.segments or [])
        ]

        # Use audio.audio_url if valid live url, otherwise world CDN url
        final_url = audio.audio_url if (audio.audio_url and not audio.audio_url.startswith("https://cdn.ettehad.app")) else live_cdn_url

        return SurahAudioResponse(
            surahId=audio.surah_id,
            reciterId=audio.reciter_id,
            audioUrl=final_url,
            durationMs=audio.duration_ms,
            segments=seg_items
        )

    @staticmethod
    async def get_user_bookmarks(db: AsyncSession, user_id: str):
        stmt = select(QuranBookmark).where(QuranBookmark.user_id == user_id)
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def toggle_bookmark(db: AsyncSession, user_id: str, surah_id: int, ayah_number: int) -> BookmarkToggleResponse:
        bm_id = f"bm_{surah_id}_{ayah_number}"
        stmt = select(QuranBookmark).where(
            QuranBookmark.user_id == user_id,
            QuranBookmark.surah_id == surah_id,
            QuranBookmark.ayah_number == ayah_number
        )
        existing = await db.scalar(stmt)
        if existing:
            await db.delete(existing)
            await db.commit()
            return BookmarkToggleResponse(isBookmarked=False, bookmarkId=None)
        else:
            bm = QuranBookmark(
                id=bm_id,
                user_id=user_id,
                surah_id=surah_id,
                ayah_number=ayah_number
            )
            db.add(bm)
            await db.commit()
            return BookmarkToggleResponse(isBookmarked=True, bookmarkId=bm_id)

    @staticmethod
    async def sync_last_read(db: AsyncSession, user_id: str, surah_id: int, ayah_number: int, page_number: int, timestamp: int):
        stmt = select(LastReadPosition).where(LastReadPosition.user_id == user_id)
        pos = await db.scalar(stmt)
        if not pos:
            pos = LastReadPosition(
                user_id=user_id,
                surah_id=surah_id,
                ayah_number=ayah_number,
                page_number=page_number,
                timestamp=timestamp
            )
            db.add(pos)
        else:
            pos.surah_id = surah_id
            pos.ayah_number = ayah_number
            pos.page_number = page_number
            pos.timestamp = timestamp

        await db.commit()
        return {"saved": True, "surahId": surah_id, "ayahNumber": ayah_number, "pageNumber": page_number}

    @staticmethod
    async def search_quran(
        db: AsyncSession,
        q: str,
        scope: str = "ALL",
        juz: Optional[int] = None
    ) -> List[QuranSearchItemDTO]:
        pattern = f"%{q}%"
        stmt = select(Ayah).options(selectinload(Ayah.surah))

        if scope == "TEXT_ARABIC":
            stmt = stmt.where(or_(Ayah.text_arabic.ilike(pattern), Ayah.text_clean.ilike(pattern)))
        elif scope == "TRANSLATION":
            stmt = stmt.where(Ayah.text_persian.ilike(pattern))
        else:  # ALL
            stmt = stmt.where(or_(
                Ayah.text_arabic.ilike(pattern),
                Ayah.text_clean.ilike(pattern),
                Ayah.text_persian.ilike(pattern)
            ))

        if juz:
            stmt = stmt.where(Ayah.juz == juz)

        stmt = stmt.limit(20)
        res = await db.execute(stmt)
        results = res.scalars().all()

        items = []
        for a in results:
            items.append(QuranSearchItemDTO(
                surahId=a.surah_id,
                surahName=a.surah.name_arabic if a.surah else f"سوره {a.surah_id}",
                ayahNumber=a.ayah_number,
                textArabic=a.text_arabic,
                textPersian=a.text_persian,
                page=a.page,
                matchScope=scope
            ))
        return items

    @staticmethod
    def _build_ayah_audio_url(reciter_id: str, surah_id: int, ayah_number: int) -> str:
        s_padded = f"{surah_id:03d}"
        a_padded = f"{ayah_number:03d}"
        reciter = (reciter_id or "parhizgar").lower()
        if "abdulbasit" in reciter:
            return f"https://everyayah.com/data/Abdul_Basit_Murattal_192kbps/{s_padded}{a_padded}.mp3"
        elif "menshawi" in reciter or "minshawi" in reciter:
            return f"https://everyayah.com/data/Minshawy_Murattal_128kbps/{s_padded}{a_padded}.mp3"
        elif "hussary" in reciter or "husary" in reciter:
            return f"https://everyayah.com/data/Husary_128kbps/{s_padded}{a_padded}.mp3"
        return f"https://everyayah.com/data/Parhizgar_48kbps/{s_padded}{a_padded}.mp3"

    @classmethod
    def _format_thematic_surah_detail(cls, ts: ThematicSurah, reciter_id: str = "parhizgar") -> ThematicSurahDetailDTO:
        ayah_dtos = []
        for a in (ts.ayahs or []):
            audio_url = a.audio_url or cls._build_ayah_audio_url(reciter_id, a.original_surah_id, a.original_ayah_number)
            ayah_dtos.append(ThematicAyahDTO(
                id=a.id,
                orderIndex=a.order_index,
                originalSurahId=a.original_surah_id,
                originalSurahName=a.original_surah_name,
                originalAyahNumber=a.original_ayah_number,
                textArabic=a.text_arabic,
                textPersian=a.text_persian,
                tafsirLesson=a.tafsir_lesson,
                reflectionQuestion=a.reflection_question,
                jevScore=a.jev_score,
                audioUrl=audio_url
            ))
        return ThematicSurahDetailDTO(
            id=ts.id,
            title=ts.title,
            topic=ts.topic,
            summary=ts.summary,
            isFeatured=bool(ts.is_featured),
            searchCount=ts.search_count or 1,
            ayahCount=len(ayah_dtos),
            ayahs=ayah_dtos,
            createdAt=ts.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if ts.created_at else ""
        )

    @classmethod
    async def generate_thematic_surah(
        cls,
        db: AsyncSession,
        topic: str,
        reciter_id: str = "parhizgar"
    ) -> ThematicSurahDetailDTO:
        clean_topic = topic.strip()
        if not clean_topic:
            clean_topic = "صبر و شکیبایی"

        # 1. Check Cache
        pattern = f"%{clean_topic}%"
        stmt = select(ThematicSurah).options(selectinload(ThematicSurah.ayahs)).where(
            or_(
                ThematicSurah.topic == clean_topic,
                ThematicSurah.title.ilike(pattern),
                ThematicSurah.topic.ilike(pattern)
            )
        )
        cached = await db.scalar(stmt)
        if cached:
            cached.search_count = (cached.search_count or 0) + 1
            await db.commit()
            await db.refresh(cached)
            return cls._format_thematic_surah_detail(cached, reciter_id)

        # 2. Extract Candidates via AI / Scholarly Tafsir Prompt
        extracted_data = await cls._extract_thematic_candidates_via_ai(db, clean_topic)
        title = extracted_data.get("title") or f"سوره مبارکه گلچین: {clean_topic}"
        summary = extracted_data.get("summary") or f"مجموعه آیات محوری قرآن کریم و پیام‌های تفسیری پیرامون {clean_topic}"
        raw_candidates = extracted_data.get("ayahs") or []

        if not raw_candidates:
            fallback = cls._fallback_extract_thematic_ayahs(clean_topic)
            title = fallback["title"]
            summary = fallback["summary"]
            raw_candidates = fallback["ayahs"]

        # 3. Jev Batch Reranking and Semantic Relevance Scoring
        # Convert raw candidates to format expected by Jev batch rerank
        eval_chunks = []
        for idx, c in enumerate(raw_candidates):
            eval_chunks.append({
                "id": idx,
                "title": f"{c.get('surahName', '')}:{c.get('ayahNumber', '')}",
                "text": f"{c.get('textArabic', '')} - {c.get('textPersian', '')}",
                "summary": c.get("tafsirLesson", "") or c.get("textPersian", ""),
                "raw_data": c
            })

        scored_chunks = await JevService.batch_rerank_chunks(
            user_query=clean_topic,
            candidate_chunks=eval_chunks,
            min_score=5,
            top_k=8
        )

        if not scored_chunks:
            scored_chunks = eval_chunks[:6]

        # 4. Sort in Mushaf order (surah_id, ayah_number) for harmonious Surah sequence
        sorted_candidates = sorted(
            scored_chunks,
            key=lambda x: (
                x.get("raw_data", {}).get("surahId", 999),
                x.get("raw_data", {}).get("ayahNumber", 999)
            )
        )

        # 5. Persist to SQLite Database
        new_surah = ThematicSurah(
            id=f"ts_{uuid.uuid4().hex[:12]}",
            title=title,
            topic=clean_topic,
            summary=summary,
            is_featured=False,
            search_count=1
        )
        db.add(new_surah)
        await db.flush()

        for idx, item in enumerate(sorted_candidates, 1):
            raw = item.get("raw_data", {})
            s_id = int(raw.get("surahId", 1))
            a_num = int(raw.get("ayahNumber", 1))
            s_name = raw.get("surahName") or f"سوره {s_id}"
            t_ar = raw.get("textArabic", "")
            t_fa = raw.get("textPersian", "")
            lesson = raw.get("tafsirLesson", "پیام هدایتی و تدبری در آیه شریفه.")
            question = raw.get("reflectionQuestion", "")
            j_score = int(item.get("jev_score", 8))
            audio = cls._build_ayah_audio_url(reciter_id, s_id, a_num)

            ta = ThematicAyah(
                thematic_surah_id=new_surah.id,
                order_index=idx,
                original_surah_id=s_id,
                original_surah_name=s_name,
                original_ayah_number=a_num,
                text_arabic=t_ar,
                text_persian=t_fa,
                tafsir_lesson=lesson,
                reflection_question=question,
                jev_score=j_score,
                audio_url=audio
            )
            db.add(ta)

        await db.commit()

        # Re-fetch with loaded ayahs
        final_stmt = select(ThematicSurah).options(selectinload(ThematicSurah.ayahs)).where(ThematicSurah.id == new_surah.id)
        saved_surah = await db.scalar(final_stmt)
        return cls._format_thematic_surah_detail(saved_surah, reciter_id)

    @classmethod
    async def _extract_thematic_candidates_via_ai(cls, db: AsyncSession, topic: str) -> Dict[str, Any]:
        system_prompt = (
            "شما یک محقق ارشد علوم قرآنی و تفسیری هستید. "
            "وظیفه شما این است که بر اساس تفاسیر معتبر (المیزان، نمونه و نور)، برای موضوع درخواستی کاربر، "
            "بین ۶ تا ۹ آیه شاخص و مرتبط از کل قرآن کریم را همراه با پیام و پند تفسیری استخراج کنید.\n"
            "پاسخ شما باید صرفاً یک آبجکت JSON معتبر به ساختار زیر باشد و هیچ متن اضافه‌ای خارج از JSON ارسال نشود:\n"
            "{\n"
            '  "title": "سوره مبارکه گلچین: [عنوان زیبا برای این سوره موضوعی]",\n'
            '  "summary": "توضیح دو خطی درباره جایگاه این موضوع در قرآن و محور مشترک آیات",\n'
            '  "ayahs": [\n'
            '    {\n'
            '      "surahId": 2,\n'
            '      "surahName": "البقرة",\n'
            '      "ayahNumber": 153,\n'
            '      "textArabic": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ...",\n'
            '      "textPersian": "ترجمه فارسی روان آیه",\n'
            '      "tafsirLesson": "پیام هدایتی و پند تفسیری استخراج شده از المیزان یا نمونه",\n'
            '      "reflectionQuestion": "پرسش تفکری پیرامون این آیه"\n'
            "    }\n"
            "  ]\n"
            "}"
        )
        ai_res = await LLMProviderService.call_chat_generation(
            section_key="quran",
            system_prompt=system_prompt,
            user_query=f"موضوع معارفی: {topic}",
            db=db
        )
        if not ai_res or not ai_res.get("text"):
            return {}

        text = ai_res["text"].strip()
        # Clean markdown codeblocks
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text)
            text = re.sub(r"```$", "", text).strip()

        try:
            return json.loads(text)
        except Exception:
            return {}

    @classmethod
    def _fallback_extract_thematic_ayahs(cls, topic: str) -> Dict[str, Any]:
        t = topic.lower()
        if any(w in t for w in ["اخوت", "برادر", "وحدت", "اتحاد", "دوست"]):
            return {
                "title": "سوره مبارکه اخوت و همبستگی ایمانی",
                "summary": "منشور قرآنی انسجام امت اسلامی، پیوند برادری ایمانی، نفی تنازع و التزام به حبل‌الله.",
                "ayahs": [
                    {
                        "surahId": 3, "surahName": "آل عمران", "ayahNumber": 103,
                        "textArabic": "وَاعْتَصِمُوا بِحَبْلِ اللَّهِ جَمِيعًا وَلَا تَفَرَّقُوا ۚ وَاذْكُرُوا نِعْمَتَ اللَّهِ عَلَيْكُمْ إِذْ كُنتُمْ أَعْدَاءً فَأَلَّفَ بَيْنَ قُلُوبِكُمْ فَأَصْبَحْتُم بِنِعْمَتِهِ إِخْوَانًا",
                        "textPersian": "و همگی به ریسمان خدا چنگ زنید و پراکنده نشوید؛ و نعمت خدا را بر خود به یاد آرید که دشمن یکدیگر بودید، و او میان دلهایتان الفت افکند و به نعمت او برادر شدید.",
                        "tafsirLesson": "تفسیر المیزان: اعتصام به حبل‌الله ضامن صیانت جامعه از تشتت است؛ الفت قلوب موهبتی الهی است که فراتر از منافع مادی عمل می‌کند.",
                        "reflectionQuestion": "چگونه می‌توانیم الفت قلبی را بر محور توحید در میان اطرافیان پایدار نگاه داریم؟"
                    },
                    {
                        "surahId": 8, "surahName": "الأنفال", "ayahNumber": 46,
                        "textArabic": "وَأَطِيعُوا اللَّهَ وَرَسُولَهُ وَلَا تَنَازَعُوا فَتَفْشَلُوا وَتَذْهَبَ رِيحُكُمْ ۖ وَاصْبِرُوا ۚ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
                        "textPersian": "و از خدا و پیامبرش اطاعت نمایید و با یکدیگر نزاع نکنید که سست می‌شوید و هیبت و قدرتتان از میان می‌رود؛ و شکیبایی ورزید که خدا با صابران است.",
                        "tafsirLesson": "تفسیر نمونه: تنازع داخلی آفت اقتدار و عزت اجتماعی است؛ راه خنثی‌سازی آن پایبندی جمعی به شکیبایی و اطاعت از اصول حق است.",
                        "reflectionQuestion": "کدام رفتارهای نسنجیده در گفتگوها منجر به شکستن اقتدار جمعی می‌شود؟"
                    },
                    {
                        "surahId": 49, "surahName": "الحجرات", "ayahNumber": 10,
                        "textArabic": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ ۚ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ",
                        "textPersian": "مؤمنان برادر یکدیگرند؛ پس میان دو برادر خود صلح و آشتی برقرار سازید و از خدا پروا کنید تا مورد رحمت قرار گیرید.",
                        "tafsirLesson": "تفسیر نور: رابطه مؤمنان با تعبیر حقوقی و عاطفی «اخوت» بیان شده است؛ اصلاح ذات‌البین یک مسئولیت فردی و اجتماعی همگانی است.",
                        "reflectionQuestion": "امروز برای ترمیم روابط برادران ایمانی چه گام عملی می‌توان برداشت؟"
                    },
                    {
                        "surahId": 59, "surahName": "الحشر", "ayahNumber": 9,
                        "textArabic": "وَالَّذِينَ تَبَوَّءُوا الدَّارَ وَالْإِيمَانَ مِن قَبْلِهِمْ يُحِبُّونَ مَنْ هَاجَرَ إِلَيْهِمْ وَلَا يَجِدُونَ فِي صُدُورِهِمْ حَاجَةً مِّمَّا أُوتُوا وَيُؤْثِرُونَ عَلَىٰ أَنفُسِهِمْ وَلَوْ كَانَ بِهِمْ خَصَاصَةٌ",
                        "textPersian": "و کسانی که پیش از مهاجران در دیار خود و در سراسر ایمان جای گرفتند، مهاجران را دوست می‌دارند و در دل‌های خود کمبودی از آنچه داده شده احساس نمی‌کنند و آنان را بر خود مقدم می‌دارند، هرچند خود نیاز مبرم داشته باشند.",
                        "tafsirLesson": "تفسیر المیزان: قله ایثار و پاکی دل از حسادت، تجلی راستین اخوت اسلامی در سیره انصار و مهاجرین است.",
                        "reflectionQuestion": "تا چه اندازه حاضریم مصلحت برادر ایمانی‌مان را بر میل شخصی خود ترجیح دهیم؟"
                    }
                ]
            }

        if any(w in t for w in ["آرامش", "ذکر", "اضطراب", "یاد خدا", "دل"]):
            return {
                "title": "سوره مبارکه یاد خدا و آرامش دل‌ها",
                "summary": "آیات نورانی تسکین قلب‌ها، جایگاه ذکر پروردگار در رفع تشویش‌ها و تجلی طمأنینه معنوی.",
                "ayahs": [
                    {
                        "surahId": 13, "surahName": "الرعد", "ayahNumber": 28,
                        "textArabic": "الَّذِينَ آمَنُوا وَتَطْمَئِنُّ قُلُوبُهُم بِذِكْرِ اللَّهِ ۗ أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ",
                        "textPersian": "همان کسانی که ایمان آورده‌اند و دل‌هایشان به یاد خدا آرام می‌گیرد؛ آگاه باشید که با یاد خدا دل‌ها آرامش می‌یابد.",
                        "tafsirLesson": "تفسیر نمونه: تنها تکیه‌گاه مطلق و بی‌زوال هستی ذات اقدس الهی است؛ دل آدمی جز با اتصال به بی‌نهایت آرام نمی‌گیرد.",
                        "reflectionQuestion": "در لحظات اوج دغدغه فکری، چگونه یاد خدا را در عمق جان جاری کنیم؟"
                    },
                    {
                        "surahId": 20, "surahName": "طه", "ayahNumber": 14,
                        "textArabic": "إِنَّنِي أَنَا اللَّهُ لَا إِلَٰهَ إِلَّا أَنَا فَاعْبُدْنِي وَأَقِمِ الصَّلَاةَ لِذِكْرِي",
                        "textPersian": "همانا من الله هستم، معبودی جز من نیست؛ پس مرا پرستش کن و برای یاد من نماز را برپا دار.",
                        "tafsirLesson": "تفسیر المیزان: غایت و حقیقت اقامه نماز، زنده نگه‌داشتن حضور قلب و ذکر مداوم معبود در متن زندگی است.",
                        "reflectionQuestion": "چگونه می‌توان کیفیت نماز را از یک عادت قالبی به منبع الهام‌بخش ذکر ارتقا داد؟"
                    },
                    {
                        "surahId": 33, "surahName": "الأحزاب", "ayahNumber": 41,
                        "textArabic": "يَا أَيُّهَا الَّذِينَ آمَنُوا اذْكُرُوا اللَّهَ ذِكْرًا كَثِيرًا وَسَبِّحُوهُ بُكْرَةً وَأَصِيلًا",
                        "textPersian": "ای کسانی که ایمان آورده‌اید! خدا را بسیار یاد کنید و او را در هر صبح و شام تسبیح گویید.",
                        "tafsirLesson": "تفسیر نور: برای بیشتر عبادات اندازه‌ای معین شده، اما برای ذکر خدا حدی تعیین نشده است؛ ذکر کثیر انسان را در حصن امان قرار می‌دهد.",
                        "reflectionQuestion": "چه برنامه‌ای برای تسبیح و تذکر بامداد و شامگاه تنظیم کرده‌ایم؟"
                    },
                    {
                        "surahId": 89, "surahName": "الفجر", "ayahNumber": 27,
                        "textArabic": "يَا أَيَّتُهَا النَّفْسُ الْمُطْمَئِنَّةُ ارْجِعِي إِلَىٰ رَبِّكِ رَاضِيَةً مَّرْضِيَّةً فَادْخُلِي فِي عِبَادِي وَادْخُلِي جَنَّتِي",
                        "textPersian": "ای نفس مطمئن و آرام‌یافته! به سوی پروردگارت بازگرد در حالی که هم تو از او خشنودی و هم او از تو خشنود است؛ پس در میان بندگانم درآی و به بهشتم وارد شو.",
                        "tafsirLesson": "تفسیر المیزان: اوج تکامل بندگی دستیابی به مقام طمأنینه و رضای متقابل با آفریدگار است.",
                        "reflectionQuestion": "چه موانعی روح را از رسیدن به طمأنینه و رضایت از تقدیرات حق بازمی‌دارد؟"
                    }
                ]
            }

        # Default: صبر و پایمردی
        return {
            "title": "سوره مبارکه صبر و پایمردی در برابر سختی‌ها",
            "summary": "آیات استقامت، مددجویی از صلات و شکیبایی، بشارت پیروزی به صابران و پیوند عزم با توکل.",
            "ayahs": [
                {
                    "surahId": 2, "surahName": "البقرة", "ayahNumber": 153,
                    "textArabic": "يَا أَيُّهَا الَّذِينَ آمَنُوا اسْتَعِينُوا بِالصَّبْرِ وَالصَّلَاةِ ۚ إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
                    "textPersian": "ای کسانی که ایمان آورده‌اید! از شکیبایی و نماز یاری جویید؛ همانا خداوند با شکیبایان است.",
                    "tafsirLesson": "تفسیر نمونه: صبر نیروی مقاومت درونی انسان در برابر موانع و گناهان است و نماز اتصال به قدرت لایزال الهی؛ تجمیع این دو شکست‌ناپذیری مؤمن را تضمین می‌کند.",
                    "reflectionQuestion": "در دشواری‌های اخیر، چقدر از اهرم نماز و شکیبایی برای آرامش بهره گرفته‌ایم؟"
                },
                {
                    "surahId": 2, "surahName": "البقرة", "ayahNumber": 155,
                    "textArabic": "وَلَنَبْلُوَنَّكُم بِشَيْءٍ مِّنَ الْخَوْفِ وَالْجُوعِ وَنَقْصٍ مِّنَ الْأَمْوَالِ وَالْأَنفُسِ وَالثَّمَرَاتِ ۗ وَبَشِّرِ الصَّابِرِينَ",
                    "textPersian": "و قطعاً شما را با چیزی از ترس، گرسنگی، و کاستی در اموال و جان‌ها و محصولات می‌آزماییم؛ و مژده ده به شکیبایان.",
                    "tafsirLesson": "تفسیر المیزان: آزمون‌های زندگی بستر رشد و فعلیت یافتن استعدادهای باطنی انسان است؛ شکیبایی کلید موفقیت در این ابتلائات است.",
                    "reflectionQuestion": "کدام یک از ناملایمات زندگی فرصتی برای پالایش روح و صبوری ما بوده است؟"
                },
                {
                    "surahId": 3, "surahName": "آل عمران", "ayahNumber": 200,
                    "textArabic": "يَا أَيُّهَا الَّذِينَ آمَنُوا اصْبِرُوا وَصَابِرُوا وَرَابِطُوا وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُفْلِحُونَ",
                    "textPersian": "ای اهل ایمان! شکیبایی پیشه کنید، در برابر دشمنان پایداری افزون‌تر نمایید، پیوندها و مرزها را پاس دارید و تقوای الهی داشته باشید، شاید رستگار شوید.",
                    "tafsirLesson": "تفسیر نور: چهار گام جامع موفقیت ایمانی: صبر فردی، هم‌افزایی صبوری جمعی (صابروا)، پیوند همبستگی (رابطوا) و رعایت تقوا.",
                    "reflectionQuestion": "چگونه می‌توانیم روحیه مقاومت جمعی را در خانواده و جامعه تقویت کنیم؟"
                },
                {
                    "surahId": 103, "surahName": "العصر", "ayahNumber": 1,
                    "textArabic": "وَالْعَصْرِ ﴿١﴾ إِنَّ الْإِنسَانَ لَفِي خُسْرٍ ﴿٢﴾ إِلَّا الَّذِينَ آمَنُوا وَعَمِلُوا الصَّالِحَاتِ وَتَوَاصَوْا بِالْحَقِّ وَتَوَاصَوْا بِالصَّبْرِ ﴿٣﴾",
                    "textPersian": "سوگند به عصر! که واقعاً انسان در زیانکاری است؛ مگر کسانی که ایمان آورده و کارهای شایسته انجام داده‌اند و یکدیگر را به حق و شکیبایی سفارش نموده‌اند.",
                    "tafsirLesson": "تفسیر نمونه: تنها راه نجات از خسران قطعی عمر، چهارگانه ایمان، عمل صالح، تواصی به حق و تواصی به صبر است.",
                    "reflectionQuestion": "چه گام عملی برای سفارش دوجانبه به حق و شکیبایی در معاشرت‌هایمان برمی‌داریم؟"
                }
            ]
        }

    @classmethod
    async def get_thematic_surahs(
        cls,
        db: AsyncSession,
        search: Optional[str] = None,
        featured_only: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ThematicSurahListItemDTO], int]:
        stmt = select(ThematicSurah).options(selectinload(ThematicSurah.ayahs))
        count_stmt = select(func.count(ThematicSurah.id))

        filters = []
        if search:
            pat = f"%{search.strip()}%"
            filters.append(or_(ThematicSurah.title.ilike(pat), ThematicSurah.topic.ilike(pat), ThematicSurah.summary.ilike(pat)))
        if featured_only:
            filters.append(ThematicSurah.is_featured == True)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))

        total_count = (await db.scalar(count_stmt)) or 0

        # Sort: featured first, then search_count desc, then created_at desc
        stmt = stmt.order_by(desc(ThematicSurah.is_featured), desc(ThematicSurah.search_count), desc(ThematicSurah.created_at))
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        res = await db.execute(stmt)
        surahs = res.scalars().all()

        items = []
        for s in surahs:
            items.append(ThematicSurahListItemDTO(
                id=s.id,
                title=s.title,
                topic=s.topic,
                summary=s.summary,
                isFeatured=bool(s.is_featured),
                searchCount=s.search_count or 1,
                ayahCount=len(s.ayahs or [])
            ))
        return items, total_count

    @classmethod
    async def get_thematic_surah_detail(
        cls,
        db: AsyncSession,
        surah_id: str,
        reciter_id: str = "parhizgar"
    ) -> Optional[ThematicSurahDetailDTO]:
        stmt = select(ThematicSurah).options(selectinload(ThematicSurah.ayahs)).where(ThematicSurah.id == surah_id)
        surah = await db.scalar(stmt)
        if not surah:
            return None
        return cls._format_thematic_surah_detail(surah, reciter_id)

    @classmethod
    async def toggle_thematic_surah_featured(
        cls,
        db: AsyncSession,
        surah_id: str,
        is_featured: Optional[bool] = None
    ) -> Optional[ThematicSurahListItemDTO]:
        stmt = select(ThematicSurah).options(selectinload(ThematicSurah.ayahs)).where(ThematicSurah.id == surah_id)
        surah = await db.scalar(stmt)
        if not surah:
            return None
        if is_featured is not None:
            surah.is_featured = is_featured
        else:
            surah.is_featured = not bool(surah.is_featured)
        await db.commit()
        await db.refresh(surah)
        return ThematicSurahListItemDTO(
            id=surah.id,
            title=surah.title,
            topic=surah.topic,
            summary=surah.summary,
            isFeatured=bool(surah.is_featured),
            searchCount=surah.search_count or 1,
            ayahCount=len(surah.ayahs or [])
        )

    @classmethod
    async def update_thematic_surah(
        cls,
        db: AsyncSession,
        surah_id: str,
        data: ThematicSurahUpdateRequest
    ) -> Optional[ThematicSurahDetailDTO]:
        stmt = select(ThematicSurah).options(selectinload(ThematicSurah.ayahs)).where(ThematicSurah.id == surah_id)
        surah = await db.scalar(stmt)
        if not surah:
            return None
        if data.title is not None:
            surah.title = data.title
        if data.summary is not None:
            surah.summary = data.summary
        if data.isFeatured is not None:
            surah.is_featured = data.isFeatured
        await db.commit()
        await db.refresh(surah)
        return cls._format_thematic_surah_detail(surah)

    @classmethod
    async def delete_thematic_surah(cls, db: AsyncSession, surah_id: str) -> bool:
        stmt = select(ThematicSurah).where(ThematicSurah.id == surah_id)
        surah = await db.scalar(stmt)
        if not surah:
            return False
        await db.delete(surah)
        await db.commit()
        return True

