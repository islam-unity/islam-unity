from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.models import (
    Surah, Ayah, AyahTadabburData, Reciter, AudioSegment,
    ThematicSurah, ThematicAyah
)
from app.services.quran_service import QuranService
from app.schemas.quran import ThematicSurahUpdateRequest
from app.db.session import get_db
from app.api.v1.admin.common import paginate

router = APIRouter()


def serialize_surah(surah: Surah) -> Dict[str, Any]:
    return {
        "id": surah.id,
        "nameArabic": surah.name_arabic,
        "name_arabic": surah.name_arabic,
        "namePersian": surah.name_persian,
        "name_persian": surah.name_persian,
        "nameTransliterated": surah.name_transliterated,
        "name_transliterated": surah.name_transliterated,
        "ayahCount": surah.ayah_count,
        "ayah_count": surah.ayah_count,
        "revelationType": surah.revelation_type,
        "revelation_type": surah.revelation_type,
        "juzNumber": surah.juz_number,
        "juz_number": surah.juz_number,
        "revelationOrder": surah.revelation_order,
        "revelation_order": surah.revelation_order,
        "startPage": surah.start_page,
        "start_page": surah.start_page,
        "endPage": surah.end_page,
        "end_page": surah.end_page,
        "summary": surah.summary
    }


def serialize_ayah(ayah: Ayah) -> Dict[str, Any]:
    return {
        "id": ayah.id,
        "surahId": ayah.surah_id,
        "surah_id": ayah.surah_id,
        "ayahNumber": ayah.ayah_number,
        "ayah_number": ayah.ayah_number,
        "textArabic": ayah.text_arabic,
        "text_arabic": ayah.text_arabic,
        "textPersian": ayah.text_persian,
        "text_persian": ayah.text_persian,
        "textClean": ayah.text_clean,
        "text_clean": ayah.text_clean,
        "juz": ayah.juz,
        "hizb": ayah.hizb,
        "page": ayah.page,
        "sajdah": ayah.sajdah
    }


def serialize_tadabbur(tadabbur: AyahTadabburData) -> Dict[str, Any]:
    return {
        "id": tadabbur.id,
        "surahId": tadabbur.surah_id,
        "surah_id": tadabbur.surah_id,
        "ayahNumber": tadabbur.ayah_number,
        "ayah_number": tadabbur.ayah_number,
        "briefTafsir": tadabbur.brief_tafsir,
        "brief_tafsir": tadabbur.brief_tafsir,
        "keywords": tadabbur.keywords or [],
        "aiTadabbur": tadabbur.ai_tadabbur or [],
        "ai_tadabbur": tadabbur.ai_tadabbur or [],
        "reflectionQuestion": tadabbur.reflection_question,
        "reflection_question": tadabbur.reflection_question,
        "relatedAyahs": tadabbur.related_ayahs or [],
        "related_ayahs": tadabbur.related_ayahs or [],
        "translations": tadabbur.translations or {}
    }


def serialize_reciter(reciter: Reciter) -> Dict[str, Any]:
    return {
        "id": reciter.id,
        "nameFa": reciter.name_fa,
        "name_fa": reciter.name_fa,
        "nameAr": reciter.name_ar,
        "name_ar": reciter.name_ar,
        "style": reciter.style,
        "bitrate": reciter.bitrate,
        "isDefault": reciter.is_default,
        "is_default": reciter.is_default
    }


def serialize_audio_segment(seg: AudioSegment) -> Dict[str, Any]:
    return {
        "id": seg.id,
        "surahId": seg.surah_id,
        "surah_id": seg.surah_id,
        "reciterId": seg.reciter_id,
        "reciter_id": seg.reciter_id,
        "audioUrl": seg.audio_url,
        "audio_url": seg.audio_url,
        "durationMs": seg.duration_ms,
        "duration_ms": seg.duration_ms,
        "segments": seg.segments or []
    }


@router.get("/surahs", summary="فهرست ۱۱۴ سوره قرآن کریم")
async def list_surahs(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(Surah).order_by(Surah.id.asc())
    surahs, meta = await paginate(db, stmt, page=page, page_size=pageSize or 114, limit=limit)
    return success_response(
        data=[serialize_surah(s) for s in surahs],
        meta=meta
    )


@router.get("/ayahs", summary="فهرست بهینه و صفحه‌بندی‌شده آیات قرآن با فیلتر سوره و جستجو")
async def list_ayahs(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    surah_id: Optional[int] = Query(None),
    surahId: Optional[int] = Query(None),
    juz: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(Ayah)

    s_id = surah_id or surahId
    if s_id is not None:
        stmt = stmt.where(Ayah.surah_id == s_id)

    if juz is not None:
        stmt = stmt.where(Ayah.juz == juz)

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Ayah.text_clean.ilike(pattern),
                Ayah.text_persian.ilike(pattern),
                Ayah.text_arabic.ilike(pattern)
            )
        )

    stmt = stmt.order_by(Ayah.surah_id.asc(), Ayah.ayah_number.asc())

    ayahs, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)
    return success_response(
        data=[serialize_ayah(a) for a in ayahs],
        meta=meta
    )


@router.get("/ayahs/{surah_id}/{ayah_number}/tadabbur", summary="دریافت داده‌های تدبر و تفسیر آیه")
async def get_ayah_tadabbur(
    surah_id: int,
    ayah_number: int,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AyahTadabburData).where(
        AyahTadabburData.surah_id == surah_id,
        AyahTadabburData.ayah_number == ayah_number
    )
    tadabbur = await db.scalar(stmt)
    if not tadabbur:
        raise HTTPException(status_code=404, detail="داده‌های تدبر برای این آیه یافت نشد.")

    return success_response(data=serialize_tadabbur(tadabbur))


@router.get("/reciters", summary="فهرست قاریان قرآن کریم و صوت‌ها")
async def list_reciters(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    reciters = (await db.scalars(select(Reciter))).all()
    return success_response(data=[serialize_reciter(r) for r in reciters])


@router.get("/audio-segments", summary="فهرست قطعات صوتی آیات قرآن")
async def list_audio_segments(
    surah_id: Optional[int] = Query(None),
    surahId: Optional[int] = Query(None),
    reciter_id: Optional[str] = Query(None),
    reciterId: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(AudioSegment)
    s_id = surah_id or surahId
    if s_id is not None:
        stmt = stmt.where(AudioSegment.surah_id == s_id)

    r_id = reciter_id or reciterId
    if r_id:
        stmt = stmt.where(AudioSegment.reciter_id == r_id)

    segments = (await db.scalars(stmt)).all()
    return success_response(data=[serialize_audio_segment(s) for s in segments])


# -------------------------------------------------------------
# Admin Thematic Surahs Endpoints (مدیریت سوره‌های موضوعی و گلچین)
# -------------------------------------------------------------

@router.get("/thematic-surahs", summary="فهرست صفحه‌بندی‌شده سوره‌های موضوعی برای پنل مدیریت")
async def list_admin_thematic_surahs(
    page: int = Query(1, ge=1),
    pageSize: Optional[int] = Query(None, ge=1, le=100),
    limit: Optional[int] = Query(None, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_featured: Optional[bool] = Query(None),
    isFeatured: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    actual_limit = pageSize or limit or 20
    feat = is_featured if is_featured is not None else isFeatured
    items, total = await QuranService.get_thematic_surahs(
        db=db,
        search=search,
        featured_only=bool(feat) if feat is not None else False,
        page=page,
        page_size=actual_limit
    )
    return success_response(
        data=[i.model_dump() for i in items],
        meta={
            "page": page,
            "pageSize": actual_limit,
            "totalCount": total,
            "total": total,
            "totalPages": (total + actual_limit - 1) // actual_limit if actual_limit > 0 else 1,
            "hasMore": page * actual_limit < total
        }
    )


@router.get("/thematic-surahs/{surah_id}", summary="دریافت شناسنامه و متن کامل سوره موضوعی برای ادمین")
async def get_admin_thematic_surah(
    surah_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    detail = await QuranService.get_thematic_surah_detail(db, surah_id)
    if not detail:
        raise HTTPException(status_code=404, detail="سوره موضوعی یافت نشد.")
    return success_response(data=detail.model_dump())


@router.patch("/thematic-surahs/{surah_id}/feature", summary="تغییر وضعیت نشان ویژه (پین) سوره موضوعی")
async def toggle_feature_thematic_surah(
    surah_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    updated = await QuranService.toggle_thematic_surah_featured(db, surah_id)
    if not updated:
        raise HTTPException(status_code=404, detail="سوره موضوعی یافت نشد.")
    return success_response(data=updated.model_dump())


@router.put("/thematic-surahs/{surah_id}", summary="ویرایش عنوان یا چکیده سوره موضوعی")
async def update_admin_thematic_surah(
    surah_id: str,
    data: ThematicSurahUpdateRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    updated = await QuranService.update_thematic_surah(db, surah_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="سوره موضوعی یافت نشد.")
    return success_response(data=updated.model_dump())


@router.delete("/thematic-surahs/{surah_id}", summary="حذف سوره موضوعی")
async def delete_admin_thematic_surah(
    surah_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    deleted = await QuranService.delete_thematic_surah(db, surah_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="سوره موضوعی یافت نشد.")
    return success_response(data={"deleted": True, "id": surah_id})

