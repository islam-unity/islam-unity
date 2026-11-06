import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.db.models import Ayah, Surah, AyahTadabburData
from app.services.agent.tools.registry import ToolSpec

logger = logging.getLogger(__name__)


async def tool_search_quran(
    query: Optional[str] = None,
    surah_id: Optional[int] = None,
    ayah_number: Optional[int] = None,
    include_tadabbur: bool = True,
    limit: int = 3,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Retrieves Quranic verses by exact surah/ayah number or textual keyword search
    across Arabic text and Persian translation. Includes Tadabbur reflections if available.
    """
    if db is None:
        return []

    # 1. Exact Ayah Lookup
    if surah_id is not None and ayah_number is not None:
        stmt = select(Ayah).where(Ayah.surah_id == surah_id, Ayah.ayah_number == ayah_number)
        res = await db.execute(stmt)
        ayah = res.scalar_one_or_none()
        if not ayah:
            return []
        
        tadabbur_notes = []
        if include_tadabbur:
            td_stmt = select(AyahTadabburData).where(
                AyahTadabburData.surah_id == surah_id,
                AyahTadabburData.ayah_number == ayah_number
            )
            td_res = await db.execute(td_stmt)
            tadabburs = td_res.scalars().all()
            tadabbur_notes = [t.reflection_text for t in tadabburs if t.reflection_text]

        return [{
            "id": f"ayah_{ayah.surah_id}_{ayah.ayah_number}",
            "surahId": ayah.surah_id,
            "ayahNumber": ayah.ayah_number,
            "textArabic": ayah.text_arabic,
            "textPersian": ayah.text_persian,
            "pageNumber": getattr(ayah, "page", getattr(ayah, "page_number", 1)),
            "tadabburNotes": tadabbur_notes
        }]

    # 2. Text Search across Ayahs
    if not query or not query.strip():
        return []

    clean_q = query.replace("؟", "").strip()
    keywords = [w.strip() for w in clean_q.split() if len(w.strip()) > 2]
    if not keywords:
        keywords = [clean_q]

    conditions = [
        or_(
            Ayah.text_clean.ilike(f"%{kw}%"),
            Ayah.text_persian.ilike(f"%{kw}%")
        )
        for kw in keywords[:3]
    ]

    stmt = select(Ayah).where(or_(*conditions)).limit(limit)
    res = await db.execute(stmt)
    ayahs = res.scalars().all()

    return [
        {
            "id": f"ayah_{a.surah_id}_{a.ayah_number}",
            "surahId": a.surah_id,
            "ayahNumber": a.ayah_number,
            "textArabic": a.text_arabic,
            "textPersian": a.text_persian,
            "pageNumber": getattr(a, "page", getattr(a, "page_number", 1))
        }
        for a in ayahs
    ]


SEARCH_QURAN_TOOL = ToolSpec(
    name="search_quran",
    description="جستجوی آیات قرآن کریم با متن عربی یا ترجمه فارسی، یا استخراج آیه مشخص با شماره سوره و آیه همراه با نکات تدبری",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "متن عربی یا ترجمه فارسی آیه جهت جستجو"
            },
            "surah_id": {
                "type": "integer",
                "description": "شماره سوره (۱ تا ۱۱۴) در صورت مشخص بودن آیه"
            },
            "ayah_number": {
                "type": "integer",
                "description": "شماره آیه در صورت مشخص بودن"
            },
            "include_tadabbur": {
                "type": "boolean",
                "description": "آیا نکات تدبری مرتبط نیز استخراج شوند یا خیر (پیش‌فرض: true)",
                "default": True
            },
            "limit": {
                "type": "integer",
                "description": "حداکثر تعداد آیات بازگشتی (پیش‌فرض: 3)",
                "default": 3
            }
        }
    },
    func=tool_search_quran,
    summarizer=lambda args, res: f"استخراج {len(res)} آیه از کلام‌الله مجید"
)
