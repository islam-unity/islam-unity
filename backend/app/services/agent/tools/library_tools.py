import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.db.models import KnowledgeChunk, Book, BookChapter
from app.services.vector_service import VectorService
from app.services.jev_service import JevService
from app.services.agent.tools.registry import ToolSpec

logger = logging.getLogger(__name__)


async def tool_search_library(
    query: str,
    madhhab: Optional[str] = None,
    major_topic: Optional[str] = None,
    limit: int = 4,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Searches the Islamic library and knowledge base using semantic vector retrieval
    and Jev decision re-ranking. Returns relevant chunks with book and chapter details.
    """
    candidates = await VectorService.search_by_representations(
        query=query,
        limit_chunks=max(8, limit * 2),
        madhhab=madhhab,
        major_topic=major_topic
    )

    if not candidates:
        # Fallback to semantic search on legacy vectors
        hits = await VectorService.search_semantic(query=query, limit=limit, madhhab=madhhab)
        return [
            {
                "chunkId": h.get("chunkId", ""),
                "bookTitle": h.get("bookTitle", "کتاب اسلامی"),
                "chapterTitle": h.get("chapterTitle", "فصل"),
                "excerpt": h.get("text", "")[:350],
                "madhhab": h.get("madhhab"),
                "pageNumber": h.get("pageNumber"),
                "score": h.get("score")
            }
            for h in hits
        ]

    # Batch rerank summaries with Jev
    ranked = await JevService.batch_rerank_chunks(
        user_query=query,
        candidate_chunks=candidates,
        min_score=5,
        top_k=limit
    )

    # Hydrate texts from DB if session is available
    results = []
    chunk_ids = [c["chunkId"] for c in ranked if c.get("chunkId")]
    db_chunks = {}
    if db is not None and chunk_ids:
        try:
            q_res = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids)))
            db_chunks = {kc.id: kc for kc in q_res.scalars().all()}
        except Exception as e:
            logger.debug(f"Could not hydrate chunks from db: {e}")

    for rc in ranked:
        cid = rc.get("chunkId", "")
        kc = db_chunks.get(cid)
        full_text = kc.full_text if kc else (rc.get("summary") or "")
        arabic_text = kc.text_arabic if kc else ""
        excerpt = f"«{arabic_text}»\n{full_text[:400]}" if arabic_text else full_text[:400]

        results.append({
            "chunkId": cid,
            "bookTitle": rc.get("bookTitle") or (kc.book_title if kc else "منبع اسلامی"),
            "chapterTitle": rc.get("chapterTitle") or (kc.chapter_title if kc else ""),
            "excerpt": excerpt,
            "fullText": full_text if len(full_text) < 1500 else full_text[:1500] + "...",
            "madhhab": rc.get("madhhab"),
            "pageNumber": rc.get("pageNumber"),
            "score": rc.get("score"),
            "jevScore": rc.get("jev_score")
        })

    return results


async def tool_read_chunk(
    chunk_id: str,
    include_neighbors: bool = True,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Reads the complete text of a specific knowledge chunk and optionally inspects
    preceding and subsequent passages for comprehensive contextual understanding.
    """
    if db is None:
        return {"error": "پایگاه داده در دسترس نیست.", "chunkId": chunk_id}

    target = await db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id))
    if not target:
        return {"error": f"بخش با شناسه '{chunk_id}' یافت نشد.", "chunkId": chunk_id}

    response_data: Dict[str, Any] = {
        "chunkId": target.id,
        "bookTitle": target.book_title,
        "chapterTitle": target.chapter_title,
        "fullText": target.full_text,
        "arabicText": target.text_arabic,
        "pageNumber": target.page_number,
        "madhhab": target.madhhab,
        "topic": target.major_topic,
        "previousContext": None,
        "nextContext": None
    }

    if include_neighbors and target.sequence_index is not None:
        try:
            prev_chunk = await db.scalar(
                select(KnowledgeChunk)
                .where(
                    KnowledgeChunk.book_id == target.book_id,
                    KnowledgeChunk.sequence_index == target.sequence_index - 1
                )
            )
            if prev_chunk:
                response_data["previousContext"] = prev_chunk.full_text[:350]

            next_chunk = await db.scalar(
                select(KnowledgeChunk)
                .where(
                    KnowledgeChunk.book_id == target.book_id,
                    KnowledgeChunk.sequence_index == target.sequence_index + 1
                )
            )
            if next_chunk:
                response_data["nextContext"] = next_chunk.full_text[:350]
        except Exception as e:
            logger.debug(f"Error reading chunk neighbors: {e}")

    return response_data


async def tool_browse_book_toc(
    book_id: Optional[str] = None,
    query: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Browses the Islamic library catalog and chapter table of contents.
    Enables the agent to inspect chapter structures and select relevant sections.
    """
    if db is None:
        return []

    if book_id:
        stmt = (
            select(BookChapter)
            .where(BookChapter.book_id == book_id)
            .order_by(BookChapter.chapter_number)
        )
        res = await db.execute(stmt)
        chapters = res.scalars().all()
        return [
            {
                "chapterId": ch.id,
                "chapterNumber": ch.chapter_number,
                "title": ch.title,
                "summary": ch.summary or "",
                "subheadings": ch.subheadings or []
            }
            for ch in chapters
        ]
    else:
        stmt = select(Book).options(selectinload(Book.chapters)).limit(15)
        res = await db.execute(stmt)
        books = res.scalars().all()
        results = []
        for b in books:
            if query and query.strip():
                q_clean = query.strip().lower()
                b_text = f"{b.title} {b.author or ''} {' '.join(b.tags or [])}".lower()
                if q_clean not in b_text:
                    continue
            results.append({
                "bookId": b.id,
                "title": b.title,
                "author": b.author,
                "language": b.language,
                "tags": b.tags or [],
                "chaptersCount": len(b.chapters),
                "sampleChapters": [ch.title for ch in b.chapters[:5]]
            })
        return results


SEARCH_LIBRARY_TOOL = ToolSpec(
    name="search_library",
    description="جستجوی معنایی و ترکیبی در کتب، فصول و مستندات کتابخانه اسلامی با امکان فیلتر مذهب و موضوع",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "عبارت یا کلمات کلیدی جستجو (فارسی یا عربی)"
            },
            "madhhab": {
                "type": "string",
                "description": "مذهب فقهی مد نظر (اختیاری): 'شافعی'، 'حنفی'، 'شیعه اثناعشری'، 'مالکی'، 'حنبلی'"
            },
            "major_topic": {
                "type": "string",
                "description": "موضوع فقهی یا معارفی (اختیاری) مانند 'طهارة'، 'صلاة'، 'صوم'، 'زکات'، 'اخلاق'"
            },
            "limit": {
                "type": "integer",
                "description": "حداکثر تعداد نتایج (پیش‌فرض: 4)",
                "default": 4
            }
        },
        "required": ["query"]
    },
    func=tool_search_library,
    summarizer=lambda args, res: f"یافتن {len(res)} بخش در کتابخانه برای «{args.get('query', '')[:25]}»"
)

READ_CHUNK_TOOL = ToolSpec(
    name="read_chunk",
    description="مطالعه متن کامل و بافتار یک بخش خاص از کتابخانه به همراه فرازهای قبل و بعد",
    parameters={
        "type": "object",
        "properties": {
            "chunk_id": {
                "type": "string",
                "description": "شناسه بخش (chunkId) استخراج‌شده از جستجوی کتابخانه"
            },
            "include_neighbors": {
                "type": "boolean",
                "description": "آیا فراز قبل و بعد برای درک کامل سیاق خوانده شود یا خیر (پیش‌فرض: true)",
                "default": True
            }
        },
        "required": ["chunk_id"]
    },
    func=tool_read_chunk,
    summarizer=lambda args, res: f"مطالعه متن کامل بخش {args.get('chunk_id')} در کتاب {res.get('bookTitle', '')}"
)

BROWSE_BOOK_TOC_TOOL = ToolSpec(
    name="browse_book_toc",
    description="مشاهده فهرست کتاب‌های معارفی یا سرفصل‌های یک کتاب مشخص جهت ردیابی دقیق ابواب فقهی و معارفی",
    parameters={
        "type": "object",
        "properties": {
            "book_id": {
                "type": "string",
                "description": "شناسه کتاب جهت دریافت فهرست کامل فصول (اختیاری)"
            },
            "query": {
                "type": "string",
                "description": "عنوان کتاب یا کلیدواژه جهت جستجو در کاتالوگ کتابخانه (اختیاری)"
            }
        }
    },
    func=tool_browse_book_toc,
    summarizer=lambda args, res: f"بررسی فهرست {len(res)} عنوان در کتب کتابخانه"
)
