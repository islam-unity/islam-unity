from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.models import Ayah, BookChapter


class RAGService:
    @staticmethod
    async def retrieve_relevant_contexts(
        db: AsyncSession,
        query: str,
        limit_ayahs: int = 3,
        limit_texts: int = 2
    ) -> Dict[str, Any]:
        """
        Retrieves relevant Quranic verses and Islamic educational texts matching the query keywords.
        """
        keywords = [w.strip() for w in query.replace("؟", "").replace("!", "").split() if len(w.strip()) > 2]
        if not keywords:
            keywords = ["وحدت", "اخلاق", "ایمان"]

        # Search in Ayahs
        conditions = [or_(Ayah.text_clean.ilike(f"%{kw}%"), Ayah.text_persian.ilike(f"%{kw}%")) for kw in keywords[:3]]
        ayah_stmt = select(Ayah).where(or_(*conditions)).limit(limit_ayahs)
        ayah_res = await db.execute(ayah_stmt)
        ayahs = ayah_res.scalars().all()

        # If none matched, fetch Surah 49:10 and 1:1
        if not ayahs:
            fallback_res = await db.execute(select(Ayah).where(Ayah.surah_id.in_([49, 1])).limit(limit_ayahs))
            ayahs = fallback_res.scalars().all()

        # Search in Library Texts
        ch_stmt = select(BookChapter).limit(limit_texts)
        ch_res = await db.execute(ch_stmt)
        chapters = ch_res.scalars().all()

        relevant_ayahs_data = [
            {
                "surahId": a.surah_id,
                "ayahNumber": a.ayah_number,
                "textArabic": a.text_arabic,
                "textPersian": a.text_persian
            } for a in ayahs
        ]

        relevant_book_texts = [
            {
                "title": ch.title,
                "excerpt": ch.content[:200]
            } for ch in chapters
        ]

        return {
            "ayahs": relevant_ayahs_data,
            "book_texts": relevant_book_texts
        }
