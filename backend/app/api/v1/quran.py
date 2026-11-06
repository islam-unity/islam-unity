import os
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, get_current_user_optional
from app.db.models import User
from app.services.quran_service import QuranService
from app.schemas.quran import (
    BookmarkToggleRequest, LastReadSyncRequest,
    ThematicSurahGenerateRequest
)
from app.core.response import success_response, error_response

router = APIRouter()


# 4.0 Quran Download & Full Offline Synchronization
@router.get("/download", summary="دانلود یکپارچه متن کامل قرآن کریم و اطلاعات آماری و ترجمه‌ها برای کش آفلاین")
async def download_quran(
    surahId: Optional[int] = Query(None, description="شناسه سوره خاص جهت دانلود تکی (۱ تا ۱۱۴)"),
    asFile: bool = Query(False, description="دریافت به صورت فایل پیوست دانلودی JSON"),
    translation: str = Query("ansarian", description="ansarian, makarem, fooladvand, all"),
    db: AsyncSession = Depends(get_db)
):
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "quran_complete.json")
    if asFile and not surahId and os.path.exists(json_path):
        return FileResponse(
            path=json_path,
            filename="quran_complete.json",
            media_type="application/json",
            headers={"Cache-Control": "public, max-age=86400"}
        )
    data = await QuranService.get_quran_download_data(db=db, surah_id=surahId, translation=translation)
    return success_response(data=data)


@router.get("/download/file", summary="دانلود مستقیم فایل استاندارد JSON کل قرآن کریم (خط عثمان طه + ترجمه‌ها)")
async def download_quran_file():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "quran_complete.json")
    if not os.path.exists(json_path):
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static", "quran_complete.json")
    if not os.path.exists(json_path):
        return error_response(code="FILE_NOT_FOUND", message="فایل جامع قرآن کریم آماده نیست.", status_code=404)
    return FileResponse(
        path=json_path,
        filename="quran_complete.json",
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@router.get("/download/surahs/{surahId}", summary="دانلود کامل آیات یک سوره به همراه ترجمه‌ها در قالب بسته آفلاین")
async def download_surah(
    surahId: int,
    translation: str = Query("all", description="ansarian, makarem, fooladvand, all"),
    db: AsyncSession = Depends(get_db)
):
    data = await QuranService.get_quran_download_data(db=db, surah_id=surahId, translation=translation)
    surahs = data.get("surahs", [])
    if not surahs:
        return error_response(code="SURAH_NOT_FOUND", message="سوره مورد نظر یافت نشد.", status_code=404)
    return success_response(data=surahs[0])


@router.get("/ayahs/{surahId}/{ayahNumber}", summary="دریافت متن آیه منفرد به همراه ترجمه‌ها و خط عثمان طه")
async def get_single_ayah(
    surahId: int,
    ayahNumber: int,
    translation: str = Query("ansarian", description="ansarian, makarem, fooladvand"),
    db: AsyncSession = Depends(get_db)
):
    ayah = await QuranService.get_ayah(db=db, surah_id=surahId, ayah_number=ayahNumber, translation=translation)
    return success_response(data=ayah.model_dump())



# 4.1 Daily Verse
@router.get("/daily-verse", summary="آیه منتخب روز همراه با ترجمه و محور مفهومی")
async def get_daily_verse(
    db: AsyncSession = Depends(get_db)
):
    daily = await QuranService.get_daily_verse(db)
    return success_response(data=daily.model_dump())


# 4.2 Surahs Directory
@router.get("/surahs", summary="فهرست ۱۱۴ سوره قرآن کریم با فیلتر جزء، ترتیب نزول و جستجو")
async def get_surahs(
    q: Optional[str] = Query(None, description="جستجو در نام عربی، فارسی یا پینگلیش"),
    revelationType: Optional[str] = Query(None, description="MAKKI | MADANI"),
    juz: Optional[int] = Query(None, ge=1, le=30),
    sort: Optional[str] = Query("MUSHAF", description="MUSHAF, REVELATION, AYAH_COUNT_DESC, AYAH_COUNT_ASC"),
    db: AsyncSession = Depends(get_db)
):
    surahs = await QuranService.get_surahs(
        db=db,
        q=q,
        revelation_type=revelationType,
        juz=juz,
        sort=sort
    )
    return success_response(data=[s.model_dump() for s in surahs])


@router.get("/surahs/{surahId}", summary="شناسنامه و معرفی کامل یک سوره")
async def get_surah_detail(
    surahId: int,
    db: AsyncSession = Depends(get_db)
):
    surah = await QuranService.get_surah_detail(db, surahId)
    return success_response(data=surah.model_dump())


# 4.3 Verses & Mushaf Pages
@router.get("/surahs/{surahId}/ayahs", summary="متن کامل آیات یک سوره به همراه ترجمه")
async def get_surah_ayahs(
    surahId: int,
    translation: str = Query("ansarian", description="ansarian, makarem, fooladvand"),
    page: Optional[int] = Query(None, ge=1),
    limit: Optional[int] = Query(None, ge=1),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    res = await QuranService.get_surah_ayahs(
        db=db,
        surah_id=surahId,
        translation=translation,
        page=page,
        limit=limit,
        user_id=current_user.id if current_user else None
    )
    return success_response(data=res.model_dump())


@router.get("/mushaf/pages/{pageNumber}", summary="دریافت آیات منطبق بر ۶۰۴ صفحه استاندارد خط عثمان طه")
async def get_mushaf_page(
    pageNumber: int,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    res = await QuranService.get_mushaf_page(
        db=db,
        page_number=pageNumber,
        user_id=current_user.id if current_user else None
    )
    return success_response(data=res.model_dump())


# 4.4 Ayah Tadabbur Tools
@router.get("/ayahs/{surahId}/{ayahNumber}/tools", summary="بسته پژوهشی و تدبر آیه (ترجمه‌های تطبیقی، تفسیر، واژگان، تدبر)")
async def get_ayah_tools(
    surahId: int,
    ayahNumber: int,
    db: AsyncSession = Depends(get_db)
):
    tools = await QuranService.get_ayah_tools(db, surahId, ayahNumber)
    return success_response(data=tools.model_dump())


# 4.5 Audio Recitations & Timings
@router.get("/audio/reciters", summary="فهرست قاریان معتبر در دسترس")
async def get_reciters(
    db: AsyncSession = Depends(get_db)
):
    reciters = await QuranService.get_reciters(db)
    return success_response(data=[r.model_dump() for r in reciters])


@router.get("/audio/surahs/{surahId}", summary="دریافت فایل صوتی سوره و زمان‌بندی میلی‌ثانیه‌ای هر آیه")
async def get_surah_audio(
    surahId: int,
    reciterId: str = Query("parhizgar", description="parhizgar, abdulbasit, menshawi, hussary"),
    db: AsyncSession = Depends(get_db)
):
    res = await QuranService.get_surah_audio(db, surahId, reciterId)
    return success_response(data=res.model_dump())


# 4.6 Bookmarks & Reading Sync
@router.get("/user/bookmarks", summary="دریافت فهرست نشان‌های قرآنی کاربر")
async def get_user_bookmarks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    bms = await QuranService.get_user_bookmarks(db, current_user.id)
    return success_response(data=[
        {
            "id": b.id,
            "surahId": b.surah_id,
            "ayahNumber": b.ayah_number,
            "createdAt": b.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        } for b in bms
    ])


@router.post("/user/bookmarks", summary="ثبت یا حذف نشان آیه (Bookmark Toggle)")
async def toggle_bookmark(
    data: BookmarkToggleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await QuranService.toggle_bookmark(db, current_user.id, data.surahId, data.ayahNumber)
    return success_response(data=res.model_dump())


@router.put("/user/last-read", summary="همگام‌سازی آخرین موقعیت مطالعه قرآن")
async def sync_last_read(
    data: LastReadSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await QuranService.sync_last_read(
        db=db,
        user_id=current_user.id,
        surah_id=data.surahId,
        ayah_number=data.ayahNumber,
        page_number=data.pageNumber,
        timestamp=data.timestamp
    )
    return success_response(data=res)


# 4.7 Quran Search Engine
@router.get("/search", summary="جستجوی پیشرفته در متن عربی، ترجمه و ریشه‌های آیات قرآن")
async def search_quran(
    q: str = Query(..., description="کلیدواژه جستجو (عربی یا ترجمه فارسی)"),
    scope: str = Query("ALL", description="ALL | TEXT_ARABIC | TRANSLATION | ROOT"),
    juz: Optional[int] = Query(None, ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    items = await QuranService.search_quran(db, q=q, scope=scope, juz=juz)
    return success_response(data=[i.model_dump() for i in items])


# 4.8 Thematic Surahs (گلچین موضوعی آیات قرآن کریم)
@router.post("/thematic-surahs/generate", summary="تولید یا بازیابی سوره موضوعی هوشمند با موتور Jev و منابع تفسیری")
async def generate_thematic_surah(
    data: ThematicSurahGenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    surah = await QuranService.generate_thematic_surah(
        db=db,
        topic=data.topic,
        reciter_id=data.reciterId or "parhizgar"
    )
    return success_response(data=surah.model_dump())


@router.get("/thematic-surahs", summary="فهرست سوره‌های موضوعی تولیدشده و شاخص")
async def get_thematic_surahs(
    q: Optional[str] = Query(None, description="جستجو در موضوع یا عنوان سوره"),
    featuredOnly: bool = Query(False, description="فقط سوره‌های ویژه و برگزیده"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    items, total = await QuranService.get_thematic_surahs(
        db=db,
        search=q,
        featured_only=featuredOnly,
        page=page,
        page_size=limit
    )
    return success_response(
        data=[i.model_dump() for i in items],
        meta={
            "page": page,
            "pageSize": limit,
            "totalCount": total,
            "totalPages": (total + limit - 1) // limit if limit > 0 else 1
        }
    )


@router.get("/thematic-surahs/{surahId}", summary="دریافت متن کامل و آیات سوره موضوعی")
async def get_thematic_surah_detail(
    surahId: str,
    reciterId: str = Query("parhizgar", description="شناسه قاری جهت تطبیق آدرس صوت"),
    db: AsyncSession = Depends(get_db)
):
    surah = await QuranService.get_thematic_surah_detail(db, surahId, reciter_id=reciterId)
    if not surah:
        return error_response(code="NOT_FOUND", message="سوره موضوعی مورد نظر یافت نشد.", status_code=404)
    return success_response(data=surah.model_dump())

