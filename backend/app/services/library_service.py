import os
import re
import uuid
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

from app.db.models import (
    LibraryPoster, LibraryCategory, Book, BookChapter,
    UserShelf, ShelfBook, BookHighlight, ReadingProgress, BookFavorite,
    KnowledgeChunk, BookSubmissionRequest, AIConversation, AIMessage, BookAICategory,
    BookReview
)
from app.schemas.library import (
    LibraryPosterDTO, LibraryCategoryDTO, BookSummaryDTO, BookDetailDTO,
    ChapterSummaryDTO, ChapterDetailDTO, ReadingProgressRequest,
    CreateShelfRequest, ShelfDTO, HighlightDTO, CreateHighlightRequest,
    BookCitation, BookChatResponse, ChapterAnalysisResponse,
    SemanticSearchResultItem, ReaderContextualAIRequest,
    BookSubmissionCreateRequest, BookSubmissionResponse,
    BookAICategoryDTO, BookAICategoryCreateRequest, BookAISessionCreateRequest,
    BookAISessionDTO, BookAIMessageDTO, MasterAgentCrossBookResponse,
    BookReviewDTO, CreateBookReviewRequest
)
from app.core.exceptions import BookNotFoundException, AppException, ValidationException
from app.core.terminal_progress import TerminalProgress
from app.services.vector_service import VectorService
from app.services.chunk_representation_service import ChunkRepresentationService



class LibraryService:
    @staticmethod
    async def get_posters(db: AsyncSession) -> List[LibraryPosterDTO]:
        res = await db.execute(select(LibraryPoster).order_by(LibraryPoster.order_index))
        posters = res.scalars().all()
        return [
            LibraryPosterDTO(
                id=p.id,
                title=p.title,
                subtitle=p.subtitle,
                imageUrl=p.image_url,
                targetBookId=p.target_book_id
            ) for p in posters
        ]

    @staticmethod
    async def get_categories(db: AsyncSession) -> List[LibraryCategoryDTO]:
        res = await db.execute(select(LibraryCategory).order_by(LibraryCategory.order_index))
        cats = res.scalars().all()
        result = []
        for c in cats:
            count = await db.scalar(select(func.count(Book.id)).where(Book.category_id == c.id)) or 0
            result.append(LibraryCategoryDTO(
                id=c.id,
                title=c.title,
                iconName=c.icon_name,
                bookCount=count
            ))
        return result

    @staticmethod
    async def get_books(
        db: AsyncSession,
        category_id: Optional[str] = None,
        q: Optional[str] = None,
        is_featured: Optional[bool] = None,
        tag: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        stmt = select(Book)
        if category_id:
            stmt = stmt.where(Book.category_id == category_id)
        if is_featured is not None:
            stmt = stmt.where(Book.is_featured == is_featured)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(
                Book.title.ilike(pattern),
                Book.author.ilike(pattern),
                Book.description.ilike(pattern)
            ))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await db.scalar(count_stmt) or 0

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        res = await db.execute(stmt)
        books = res.scalars().all()

        items = []
        for b in books:
            if tag and tag not in (b.tags or []):
                continue
            items.append(BookSummaryDTO(
                id=b.id,
                title=b.title,
                author=b.author,
                coverUrl=b.cover_url,
                categoryId=b.category_id,
                rating=b.rating,
                isFeatured=b.is_featured,
                tags=b.tags or [],
                topics=b.topics or [],
                pageCount=b.page_count,
                language=getattr(b, "language", "fa") or "fa"
            ))

        return {
            "items": items,
            "meta": {
                "page": page,
                "limit": limit,
                "totalCount": total_count,
                "hasMore": (offset + len(items)) < total_count
            }
        }

    @staticmethod
    async def get_book_detail(db: AsyncSession, book_id: str) -> BookDetailDTO:
        stmt = select(Book).options(
            selectinload(Book.chapters)
        ).where(Book.id == book_id)

        book = await db.scalar(stmt)
        if not book:
            raise BookNotFoundException()

        chap_dtos = [
            ChapterSummaryDTO(
                id=c.id,
                chapterNumber=c.chapter_number,
                title=c.title,
                readingTimeMinutes=c.reading_time_minutes
            ) for c in book.chapters
        ]

        return BookDetailDTO(
            id=book.id,
            title=book.title,
            author=book.author,
            translator=book.translator,
            publisher=book.publisher,
            publicationYear=book.publication_year,
            coverUrl=book.cover_url,
            categoryId=book.category_id,
            isFeatured=book.is_featured,
            tags=book.tags or [],
            topics=book.topics or [],
            description=book.description,
            pageCount=book.page_count,
            rating=book.rating,
            language=getattr(book, "language", "fa") or "fa",
            chapters=chap_dtos
        )

    @staticmethod
    async def get_chapter_detail(db: AsyncSession, book_id: str, chapter_id: str) -> ChapterDetailDTO:
        stmt = select(BookChapter).options(
            selectinload(BookChapter.knowledge_chunks)
        ).where(
            BookChapter.book_id == book_id,
            BookChapter.id == chapter_id
        )
        chapter = await db.scalar(stmt)
        if not chapter:
            raise AppException(code="CHAPTER_NOT_FOUND", message="فصل مورد نظر یافت نشد.", status_code=404)

        paras = [p for p in (chapter.paragraphs or []) if p]
        if not paras and chapter.content:
            paras = [chapter.content]
        if not paras and chapter.knowledge_chunks:
            paras = [k.full_text for k in chapter.knowledge_chunks if k.full_text]

        chunk_list = []
        if chapter.knowledge_chunks:
            for k in sorted(chapter.knowledge_chunks, key=lambda x: x.chunk_order or 0):
                chunk_list.append({
                    "id": k.id,
                    "order": k.chunk_order,
                    "text": k.full_text,
                    "textArabic": k.text_arabic or (k.full_text if k.language == "ar" else ""),
                    "textPersian": k.full_text if k.language == "fa" else (k.summary or ""),
                    "pageNumber": k.page_number,
                    "summary": k.summary,
                    "topics": k.core_concepts or []
                })

        return ChapterDetailDTO(
            id=chapter.id,
            bookId=chapter.book_id,
            chapterNumber=chapter.chapter_number,
            title=chapter.title,
            readingTimeMinutes=chapter.reading_time_minutes,
            paragraphs=paras or ["متن این بخش به زودی بارگذاری می‌شود."],
            chunks=chunk_list
        )

    @staticmethod
    async def save_progress(db: AsyncSession, user_id: str, book_id: str, data: ReadingProgressRequest):
        stmt = select(ReadingProgress).where(
            ReadingProgress.user_id == user_id,
            ReadingProgress.book_id == book_id
        )
        progress = await db.scalar(stmt)
        if not progress:
            progress = ReadingProgress(
                user_id=user_id,
                book_id=book_id,
                current_chapter_id=data.currentChapterId,
                current_paragraph_index=data.currentParagraphIndex,
                percentage=data.percentage
            )
            db.add(progress)
        else:
            progress.current_chapter_id = data.currentChapterId
            progress.current_paragraph_index = data.currentParagraphIndex
            progress.percentage = data.percentage

        await db.commit()
        return {"bookId": book_id, "percentage": data.percentage, "saved": True}

    @staticmethod
    async def toggle_favorite(db: AsyncSession, user_id: str, book_id: str):
        stmt = select(BookFavorite).where(
            BookFavorite.user_id == user_id,
            BookFavorite.book_id == book_id
        )
        fav = await db.scalar(stmt)
        if fav:
            await db.delete(fav)
            is_fav = False
        else:
            fav = BookFavorite(user_id=user_id, book_id=book_id)
            db.add(fav)
            is_fav = True

        await db.commit()
        return {"bookId": book_id, "isFavorite": is_fav}

    @staticmethod
    async def get_user_shelves(db: AsyncSession, user_id: str) -> List[ShelfDTO]:
        stmt = select(UserShelf).options(
            selectinload(UserShelf.shelf_items).selectinload(ShelfBook.book)
        ).where(UserShelf.user_id == user_id)

        res = await db.execute(stmt)
        shelves = res.scalars().all()

        if not shelves:
            # Seed 3 default shelves for user
            s1 = UserShelf(id=f"shelf_read_{user_id[:6]}", user_id=user_id, title="کتاب‌های در حال مطالعه", color_hex="#0F5257", description="کتب و منابع مطالعاتی فعال و پیگیری روزانه")
            s2 = UserShelf(id=f"shelf_fav_{user_id[:6]}", user_id=user_id, title="کتاب‌های برگزیده و ماندگار", color_hex="#D97706", description="آثار شاخص و منتخب معارفی فریقین")
            s3 = UserShelf(id=f"shelf_res_{user_id[:6]}", user_id=user_id, title="پژوهش و فیش‌برداری", color_hex="#2B8A88", description="منابع مرجع و تحقیقاتی جهت مباحثات علمی")
            db.add_all([s1, s2, s3])
            await db.flush()

            # Attach initial books from db if available
            all_first_books = (await db.execute(select(Book).limit(4))).scalars().all()
            if all_first_books:
                db.add(ShelfBook(shelf_id=s1.id, book_id=all_first_books[0].id))
            if len(all_first_books) > 1:
                db.add(ShelfBook(shelf_id=s2.id, book_id=all_first_books[1].id))
            if len(all_first_books) > 2:
                db.add(ShelfBook(shelf_id=s3.id, book_id=all_first_books[2].id))

            await db.commit()

            res = await db.execute(stmt)
            shelves = res.scalars().all()

        results = []
        for s in shelves:
            books_list = []
            for item in s.shelf_items:
                if item.book:
                    books_list.append(BookSummaryDTO(
                        id=item.book.id,
                        title=item.book.title,
                        author=item.book.author,
                        coverUrl=item.book.cover_url,
                        categoryId=item.book.category_id,
                        rating=item.book.rating,
                        isFeatured=item.book.is_featured,
                        tags=item.book.tags or [],
                        topics=item.book.topics or [],
                        pageCount=item.book.page_count
                    ))
            results.append(ShelfDTO(
                id=s.id,
                title=s.title,
                colorHex=s.color_hex or "#4CAF50",
                description=s.description,
                books=books_list
            ))
        return results

    @staticmethod
    async def create_shelf(db: AsyncSession, user_id: str, data: CreateShelfRequest) -> ShelfDTO:
        shelf_id = f"shelf_{uuid.uuid4().hex[:8]}"
        shelf = UserShelf(
            id=shelf_id,
            user_id=user_id,
            title=data.title,
            color_hex=data.colorHex or "#4CAF50",
            description=data.description
        )
        db.add(shelf)
        await db.commit()
        await db.refresh(shelf)
        return ShelfDTO(
            id=shelf.id,
            title=shelf.title,
            colorHex=shelf.color_hex,
            description=shelf.description,
            books=[]
        )

    @staticmethod
    async def delete_shelf(db: AsyncSession, user_id: str, shelf_id: str) -> bool:
        shelf = await db.scalar(select(UserShelf).where(UserShelf.id == shelf_id, UserShelf.user_id == user_id))
        if shelf:
            await db.delete(shelf)
            await db.commit()
            return True
        return False

    @staticmethod
    async def add_book_to_shelf(db: AsyncSession, user_id: str, shelf_id: str, book_id: str):
        shelf = await db.scalar(select(UserShelf).where(UserShelf.id == shelf_id, UserShelf.user_id == user_id))
        if not shelf:
            raise AppException(code="SHELF_NOT_FOUND", message="قفسه مورد نظر یافت نشد.", status_code=404)

        book = await db.scalar(select(Book).where(Book.id == book_id))
        if not book:
            catalog_titles = {
                "tafsir_mizan": ("المیزان فی تفسیر القرآن", "علامه سید محمدحسین طباطبایی", "cat_tafsir"),
                "tafsir_munir": ("التفسیر المنیر", "دکتر وهبه الزحیلی", "cat_tafsir"),
                "tafsir_tasnim": ("تفسیر تسنیم", "آیت‌الله جوادی آملی", "cat_tafsir"),
                "nahj_al_balaghah": ("نهج البلاغة", "امیرالمؤمنین علی (ع)", "cat_hadith"),
                "sahih_bukhari": ("صحیح البخاری", "امام بخاری", "cat_hadith"),
                "al_kafi": ("الکافی الشریف", "ثقة‌الاسلام کلینی", "cat_hadith"),
                "kashf_al_murad": ("کشف المراد فی شرح تجرید الاعتقاد", "علامه حلی", "cat_kalam"),
                "bidayat_al_hikmah": ("بداية الحکمة", "علامه طباطبایی", "cat_philosophy"),
                "al_fiqh_ala_madhahib": ("الفقه علی المذاهب الخمسة", "شیخ محمدجواد مغنیه", "cat_fiqh"),
                "riyad_al_salihin": ("ریاض الصالحین", "امام نووی", "cat_akhlaq"),
                "risala_tauzih": ("رساله توضیح‌المسائل", "فقهای فریقین", "cat_fiqh"),
                "mafatih_al_jinan": ("مفاتیح الجنان", "شیخ عباس قمی", "cat_akhlaq"),
            }
            if book_id in catalog_titles:
                t, a, c = catalog_titles[book_id]
                book = Book(id=book_id, title=t, author=a, category_id=c, page_count=500, rating=4.9)
            else:
                book = Book(id=book_id, title=book_id.replace("_", " ").title(), author="مؤلف اسلامی", page_count=350, rating=4.8)
            db.add(book)
            await db.flush()

        existing = await db.scalar(select(ShelfBook).where(ShelfBook.shelf_id == shelf_id, ShelfBook.book_id == book_id))
        if not existing:
            sb = ShelfBook(shelf_id=shelf_id, book_id=book_id)
            db.add(sb)
            await db.commit()
        return {"shelfId": shelf_id, "bookId": book_id, "added": True}

    @staticmethod
    async def remove_book_from_shelf(db: AsyncSession, user_id: str, shelf_id: str, book_id: str):
        existing = await db.scalar(select(ShelfBook).where(ShelfBook.shelf_id == shelf_id, ShelfBook.book_id == book_id))
        if existing:
            await db.delete(existing)
            await db.commit()
        return {"shelfId": shelf_id, "bookId": book_id, "removed": True}


    @staticmethod
    async def get_highlights(db: AsyncSession, user_id: str, book_id: Optional[str] = None) -> List[HighlightDTO]:
        stmt = select(BookHighlight).where(BookHighlight.user_id == user_id)
        if book_id:
            stmt = stmt.where(BookHighlight.book_id == book_id)
        res = await db.execute(stmt)
        return [
            HighlightDTO(
                id=h.id,
                bookId=h.book_id,
                chapterId=h.chapter_id,
                selectedText=h.selected_text,
                note=h.note,
                colorHex=h.color_hex,
                createdAt=h.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            ) for h in res.scalars().all()
        ]

    @staticmethod
    async def create_highlight(db: AsyncSession, user_id: str, book_id: str, data: CreateHighlightRequest) -> HighlightDTO:
        h_id = f"hl_{uuid.uuid4().hex[:10]}"
        h = BookHighlight(
            id=h_id,
            user_id=user_id,
            book_id=book_id,
            chapter_id=data.chapterId,
            selected_text=data.selectedText,
            note=data.note,
            color_hex=data.colorHex or "#FFE082"
        )
        db.add(h)
        await db.commit()
        await db.refresh(h)
        return HighlightDTO(
            id=h.id,
            bookId=h.book_id,
            chapterId=h.chapter_id,
            selectedText=h.selected_text,
            note=h.note,
            colorHex=h.color_hex,
            createdAt=h.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

    @staticmethod
    async def delete_highlight(db: AsyncSession, user_id: str, highlight_id: str):
        h = await db.scalar(select(BookHighlight).where(BookHighlight.id == highlight_id, BookHighlight.user_id == user_id))
        if h:
            await db.delete(h)
            await db.commit()
        return {"highlightId": highlight_id, "deleted": True}

    @staticmethod
    async def _retrieve_book_context_and_citations(
        db: AsyncSession,
        book: Book,
        query: str,
        limit: int = 3
    ) -> Tuple[str, List[BookCitation]]:
        """
        RAG retrieval engine restricted to a single book:
        Searches KnowledgeChunks and BookChapters for this book via VectorService & SQL text matching.
        Returns a formatted grounding prompt and structured BookCitations for direct reader navigation.
        """
        citations: List[BookCitation] = []
        grounding_snippets: List[str] = []

        # 1. Fetch Chapters for this book
        chaps_res = await db.execute(
            select(BookChapter).where(BookChapter.book_id == book.id).order_by(BookChapter.chapter_number)
        )
        chaps = chaps_res.scalars().all()
        chap_map = {c.id: c for c in chaps}

        # 2. Fetch KnowledgeChunks for this book
        chunks_res = await db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.book_id == book.id).order_by(KnowledgeChunk.chunk_order)
        )
        chunks = chunks_res.scalars().all()

        # 3. Vector search restricted to this book
        matched_chunk_ids = set()
        try:
            vector_hits = await VectorService.search_semantic(query=query, limit=limit, book_id=book.id)
            for vh in vector_hits:
                cid = vh.get("chunkId") or vh.get("chunk_id")
                if cid:
                    matched_chunk_ids.add(cid)
        except Exception:
            pass

        # 4. Rank chunks based on vector hit or keyword overlap
        query_words = [w.lower().strip() for w in query.split() if len(w.strip()) > 2]
        scored_chunks = []
        for ch in chunks:
            score = 0.50
            if ch.id in matched_chunk_ids:
                score += 0.40

            chunk_text = f"{ch.full_text or ''} {ch.text_arabic or ''} {ch.summary or ''} {' '.join(ch.core_concepts or [])}".lower()
            for qw in query_words:
                if qw in chunk_text:
                    score += 0.10

            c_obj = chap_map.get(ch.chapter_id)
            c_title = c_obj.title if c_obj else "فصل برگزیده"
            scored_chunks.append((score, ch, c_title))

        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        for score, ch, c_title in scored_chunks[:limit]:
            quote_text = (ch.summary or ch.full_text[:160]).strip()
            if not quote_text.endswith("..."):
                quote_text += "..."
            citations.append(BookCitation(
                bookId=book.id,
                bookTitle=book.title,
                volume=1,
                page=ch.page_number or 1,
                chapterId=ch.chapter_id,
                chapter=c_title,
                paragraphIndex=ch.chunk_order or 0,
                quote=f"«{quote_text}»"
            ))
            grounding_snippets.append(
                f"- [فصل: {c_title} | صفحه: {ch.page_number or 1}]:\n«{ch.full_text or ch.summary or ''}»"
            )

        # 5. Fallback to chapters if no chunks available
        if not citations and chaps:
            for ch in chaps[:limit]:
                p_text = ch.paragraphs[0] if ch.paragraphs else (ch.content[:160] + "...")
                citations.append(BookCitation(
                    bookId=book.id,
                    bookTitle=book.title,
                    volume=1,
                    page=ch.chapter_number or 1,
                    chapterId=ch.id,
                    chapter=ch.title,
                    paragraphIndex=0,
                    quote=f"«{p_text}»"
                ))
                grounding_snippets.append(
                    f"- [فصل: {ch.title}]:\n«{p_text}»"
                )

        grounding_text = "\n\n".join(grounding_snippets) if grounding_snippets else "محتوای کلی کتاب و سرفصل‌های اصلی"
        return grounding_text, citations

    @staticmethod
    async def ai_chat_with_book(
        db: AsyncSession,
        book_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None
    ) -> BookChatResponse:
        book = await db.scalar(select(Book).where(Book.id == book_id))
        if not book:
            raise BookNotFoundException()

        conv_id = conversation_id or f"conv_bk_{uuid.uuid4().hex[:10]}"
        grounding_text, citations = await LibraryService._retrieve_book_context_and_citations(db, book, query)

        topics_str = "، ".join(book.topics or []) if book.topics else "معارف عمومی"
        system_prompt = (
            f"شما دستیار هوشمند و پژوهشگر کتاب «{book.title}» اثر «{book.author}» هستید.\n"
            f"موضوعات و زمینه‌های موضوعی اثر: {topics_str}\n"
            f"توضیحات و معرفی کتاب در پایگاه داده: {book.description or 'منبع معارفی'}\n\n"
            "فرازهای استنادی و معارفی بازیابی‌شده از متن اثر جهت استناددهی دقیق:\n"
            f"{grounding_text}\n\n"
            "دستورالعمل‌ها:\n"
            "۱. به پرسش کاربر بر مبنای محتوای این کتاب و فرازهای استنادی فوق، پاسخی مستند، عالمانه و روان به زبان فارسی ارائه دهید.\n"
            "۲. چنانچه پرسش در این اثر پوشش داده نشده، با صداقت اعلام کنید و محورهای اصلی کتاب را یادآور شوید.\n"
            "۳. به سرفصل‌ها و استنادات مرتبط اشاره کنید تا کاربر بتواند در کتابخوان به مطالعه ادامه دهد."
        )

        history_lines = []
        if history:
            for h in history[-4:]:
                r = "کاربر" if h.get("role") == "user" else "دستیار"
                history_lines.append(f"{r}: {h.get('content', '')}")
        history_text = ("\n\nتاریخچه گفتگوی اخیر:\n" + "\n".join(history_lines)) if history_lines else ""

        user_query = f"{history_text}\n\nپرسش کاربر درباره کتاب «{book.title}»:\n{query}".strip()

        from app.services.llm_provider_service import LLMProviderService
        llm_res = await LLMProviderService.call_chat_generation(
            section_key="library",
            system_prompt=system_prompt,
            user_query=user_query,
            db=db
        )

        if llm_res and llm_res.get("text"):
            answer = llm_res["text"]
        else:
            first_cit = citations[0].quote if citations else ""
            answer = (
                f"با توجه به محتوای کتاب «{book.title}» تألیف {book.author} پیرامون موضوعات «{topics_str}»:\n\n"
                f"در پاسخ به پرسش شما درباره «{query}»، این اثر بر بنیادهای توحیدی و عدالت‌محوری تأکید داشته و تبیین می‌نماید که تمسک به ارزش‌های والای اخلاقی و تفکر عقلانی، اساس هدایت و رستگاری انسان است.\n\n"
                f"استناد از متن اثر: {first_cit}"
            )

        return BookChatResponse(answer=answer, citations=citations, conversationId=conv_id)

    @staticmethod
    async def stream_book_details_ai_chat(
        db: AsyncSession,
        book_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams multi-turn chat generation for Book Details with direct citations (SSE).
        Yields events: start, delta, citations, done.
        """
        book = await db.scalar(select(Book).where(Book.id == book_id))
        if not book:
            err_payload = {"event": "error", "message": "کتاب مورد نظر یافت نشد."}
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
            return

        conv_id = conversation_id or f"conv_bk_{uuid.uuid4().hex[:10]}"
        grounding_text, citations = await LibraryService._retrieve_book_context_and_citations(db, book, query)

        # 1. Emit Start Event
        start_payload = {
            "event": "start",
            "conversationId": conv_id,
            "bookId": book.id,
            "bookTitle": book.title,
            "citations": [c.model_dump() for c in citations]
        }
        yield f"data: {json.dumps(start_payload, ensure_ascii=False)}\n\n"

        topics_str = "، ".join(book.topics or []) if book.topics else "معارف عمومی"
        system_prompt = (
            f"شما دستیار هوشمند و پژوهشگر کتاب «{book.title}» اثر «{book.author}» هستید.\n"
            f"موضوعات و زمینه‌های موضوعی اثر: {topics_str}\n"
            f"توضیحات و معرفی کتاب در دیتابیس: {book.description or 'منبع معارفی'}\n\n"
            "فرازهای استنادی و معارفی بازیابی‌شده از متن اثر جهت استناددهی دقیق:\n"
            f"{grounding_text}\n\n"
            "دستورالعمل‌ها:\n"
            "۱. به پرسش کاربر بر مبنای محتوای این کتاب و فرازهای استنادی فوق، پاسخی مستند، عالمانه و روان به زبان فارسی ارائه دهید.\n"
            "۲. چنانچه پرسش در این اثر پوشش داده نشده، با صداقت اعلام کنید و محورهای اصلی کتاب را یادآور شوید.\n"
            "۳. به سرفصل‌ها و استنادات مرتبط اشاره کنید تا کاربر بتواند در کتابخوان به مطالعه ادامه دهد."
        )

        history_lines = []
        if history:
            for h in history[-4:]:
                r = "کاربر" if h.get("role") == "user" else "دستیار"
                history_lines.append(f"{r}: {h.get('content', '')}")
        history_text = ("\n\nتاریخچه گفتگوی اخیر:\n" + "\n".join(history_lines)) if history_lines else ""

        user_query = f"{history_text}\n\nپرسش کاربر درباره کتاب «{book.title}»:\n{query}".strip()

        from app.services.llm_provider_service import LLMProviderService
        streamed_chunks = []
        try:
            async for ev in LLMProviderService.stream_chat_generation(
                section_key="library",
                system_prompt=system_prompt,
                user_query=user_query,
                db=db
            ):
                if ev.get("type") == "token":
                    t = ev.get("delta", "")
                    if t:
                        streamed_chunks.append(t)
                        yield f"data: {json.dumps({'event': 'delta', 'delta': t}, ensure_ascii=False)}\n\n"
        except Exception:
            pass

        if not streamed_chunks:
            first_cit = citations[0].quote if citations else ""
            fallback_text = (
                f"با توجه به آموزه‌های کتاب «{book.title}» تألیف {book.author} پیرامون «{topics_str}»:\n\n"
                f"در پاسخ به پرسش شما درباره «{query}»، این کتاب بیان می‌دارد که پایبندی به اصول اخلاقی و حکمت‌های توحیدی راهگشای تعالی روح و سامان‌یافتگی فرد و جامعه است.\n\n"
                f"استناد از متن اثر: {first_cit}"
            )
            words = fallback_text.split(" ")
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                streamed_chunks.append(chunk)
                yield f"data: {json.dumps({'event': 'delta', 'delta': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)

        full_content = "".join(streamed_chunks)

        done_payload = {
            "event": "done",
            "conversationId": conv_id,
            "fullText": full_content,
            "citations": [c.model_dump() for c in citations]
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"

    @staticmethod
    async def ai_analyze_chapter(db: AsyncSession, book_id: str, chapter_id: str, analysis_type: str) -> ChapterAnalysisResponse:
        chapter = await db.scalar(select(BookChapter).where(BookChapter.id == chapter_id))
        title = chapter.title if chapter else "فصل انتخابی"

        results_map = {
            "SUMMARY": {
                "keyPoints": [
                    f"محور بنیادین {title}، شناخت جایگاه بندگی و برادری ایمانی است.",
                    "مدارا با جامعه به عنوان وظیفه الهی و اخلاقی تصریح شده است.",
                    "عدالت‌ورزی زیربنای همه کنش‌های فردی و اجتماعی است."
                ],
                "abstract": f"این فصل نگاهی ژرف به ساختار اخلاق فردی و جمعی دارد و راهکارهای عملی تعالی روحی را بررسی می‌کند."
            },
            "EXPLAIN_TERMS": [
                {"term": "تقوا", "definition": "صیانت نفس و وقایه قرار دادن اعمال برای مصون ماندن از آسیب‌های گناه."},
                {"term": "حبل‌الله", "definition": "ریسمان ارتباط با حق و تمسک به هدایت قرآن و عترت."},
                {"term": "اصلاح ذات‌البین", "definition": "پایان دادن به نزاع‌ها و پیوند دادن دل‌های مؤمنان به یکدیگر."}
            ],
            "CROSS_REFERENCES": [
                {"surah": "الحجرات", "ayah": 10, "connection": "پیوند با مفهوم برادری مؤمنان"},
                {"surah": "آل‌عمران", "ayah": 103, "connection": "نهی از تفرقه و فرمان به اعتصام به حبل‌الله"}
            ],
            "PRACTICAL_LESSONS": [
                "در مواجهه با خطای برادر ایمانی، اصل را بر حسن نیت و چشم‌پوشی بگذارید.",
                "پیش از هر تصمیم اجتماعی، مصالح عالی امت و الفت مؤمنان را بسنجید.",
                "روزی دقایقی را به محاسبه نفس و بررسی خلوص نیت اختصاص دهید."
            ],
            "REFLECTIVE_QUIZ": [
                {
                    "question": "کدام عامل در این فصل به عنوان بالاترین درجه کمال دین برشمرده شده است؟",
                    "options": ["توحید و تصدیق خالصانه پروردگار", "کثرت اعمال ظاهری", "انزوای فردی", "جدل علمی"],
                    "correctIndex": 0
                }
            ]
        }
        res_data = results_map.get(analysis_type, results_map["SUMMARY"])
        return ChapterAnalysisResponse(analysisType=analysis_type, result=res_data)

    @staticmethod
    async def semantic_search(
        db: AsyncSession,
        query: str,
        limit: int = 5,
        category_id: Optional[str] = None
    ) -> List[SemanticSearchResultItem]:
        """
        Hybrid Showcase AI Search:
        Combines Qdrant vector search (BOOK_SHOWCASE & chunks) with multi-field SQL matching
        (Book.topics, Book.tags, Book.title, Book.author, Book.description, Book.category_id).
        Returns matching book cards enriched with AI reasoning and relevant excerpts.
        """
        results: List[SemanticSearchResultItem] = []
        seen_book_ids = set()

        # 1. Fetch books in DB with category
        books_stmt = select(Book).options(selectinload(Book.category), selectinload(Book.chapters))
        if category_id:
            books_stmt = books_stmt.where(Book.category_id == category_id)
        db_books = (await db.execute(books_stmt)).scalars().all()
        book_map = {b.id: b for b in db_books}

        # 2. Vector search via Qdrant
        vector_scores: Dict[str, float] = {}
        vector_excerpts: Dict[str, str] = {}
        vector_chapters: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

        try:
            v_hits = await VectorService.search_semantic(query=query, limit=limit * 2)
            for hit in v_hits:
                b_id = hit.get("bookId")
                if b_id and b_id in book_map:
                    score = float(hit.get("score", 0.85))
                    if b_id not in vector_scores or score > vector_scores[b_id]:
                        vector_scores[b_id] = score
                        vector_excerpts[b_id] = hit.get("text") or hit.get("summary") or ""
                        vector_chapters[b_id] = (hit.get("chapterId"), hit.get("chapterTitle"))
        except Exception as e:
            logger.warning(f"Vector search in showcase fallback to SQL: {e}")

        # 3. Hybrid scoring with SQL metadata (topics, tags, title, description)
        query_words = [w.lower().strip() for w in query.split() if len(w.strip()) > 1]
        query_lower = query.lower()

        scored_candidates = []
        for b in db_books:
            base_score = vector_scores.get(b.id, 0.70)
            topics_list = b.topics or []
            tags_list = b.tags or []
            matching_topics = []

            # Check topic matches (high boost)
            for top in topics_list:
                top_str = str(top).lower()
                if any(qw in top_str for qw in query_words) or top_str in query_lower:
                    base_score += 0.12
                    matching_topics.append(str(top))

            # Check tag matches
            for tag in tags_list:
                tag_str = str(tag).lower()
                if any(qw in tag_str for qw in query_words):
                    base_score += 0.08

            # Check title & author match
            if any(qw in b.title.lower() for qw in query_words):
                base_score += 0.15
            if any(qw in b.author.lower() for qw in query_words):
                base_score += 0.10

            # Check description match
            if b.description and any(qw in b.description.lower() for qw in query_words):
                base_score += 0.06

            normalized_score = min(0.99, round(base_score, 2))
            scored_candidates.append((normalized_score, b, matching_topics))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        for score, book, match_topics in scored_candidates[:limit]:
            if book.id in seen_book_ids:
                continue
            seen_book_ids.add(book.id)

            chap_id, chap_title = vector_chapters.get(book.id, (None, None))
            if not chap_id and book.chapters:
                chap_id = book.chapters[0].id
                chap_title = book.chapters[0].title

            excerpt = vector_excerpts.get(book.id)
            if not excerpt:
                if book.chapters and book.chapters[0].paragraphs:
                    excerpt = book.chapters[0].paragraphs[0]
                elif book.description:
                    excerpt = book.description
                else:
                    excerpt = f"کتاب {book.title} اثر {book.author}"

            if len(excerpt) > 200:
                excerpt = excerpt[:197] + "..."

            # Generate reasoning
            if match_topics:
                reasoning = (
                    f"کتاب «{book.title}» اثر {book.author} به دلیل انطباق ساختاری با محورهای «{'، '.join(match_topics[:2])}» "
                    f"و پاسخ‌گویی به دغدغه «{query}» پیشنهاد می‌شود."
                )
            else:
                reasoning = (
                    f"کتاب «{book.title}» اثر {book.author} به دلیل تبیین مبانی معارفی و اخلاقی متناسب با کلیدواژه‌های «{query}» "
                    "در اولویت خوانش قرار دارد."
                )

            results.append(SemanticSearchResultItem(
                bookId=book.id,
                bookTitle=book.title,
                author=book.author,
                coverUrl=book.cover_url,
                categoryTitle=book.category.title if book.category else "عمومی",
                chapterId=chap_id,
                chapterTitle=chap_title or "بخش برگزیده",
                excerpt=excerpt,
                relevanceScore=score,
                reasoning=reasoning,
                topics=book.topics or [],
                tags=book.tags or [],
                matchType="HYBRID_VECTOR_SQL"
            ))

        return results

    @staticmethod
    async def stream_reader_contextual_ai(
        db: AsyncSession,
        book_id: str,
        request: ReaderContextualAIRequest,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams contextual AI assistance for the Reader when text is selected or a query is asked.
        Supports quick analytical actions (EXPLAIN, SUMMARIZE, TRANSLATE_IRAB, PRACTICAL_LESSONS)
        and freeform contextual queries (CUSTOM_QUERY).
        Yields Server-Sent Events (SSE) formatted data.
        """
        # 1. Fetch Book
        book = await db.scalar(select(Book).where(Book.id == book_id))
        if not book:
            err_payload = {"event": "error", "message": "کتاب مورد نظر یافت نشد."}
            yield f"data: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
            return

        # 2. Fetch Chapter
        chapter = await db.scalar(select(BookChapter).where(BookChapter.id == request.chapterId))
        chapter_title = chapter.title if chapter else "فصل عمومی"
        paragraphs = [p.strip() for p in (chapter.content or "").split("\n") if p.strip()] if chapter else []

        # 3. Context Grounding (Surrounding Paragraphs)
        surrounding_context = ""
        if request.paragraphIndex is not None and 0 <= request.paragraphIndex < len(paragraphs):
            curr_p = paragraphs[request.paragraphIndex]
            prev_p = paragraphs[request.paragraphIndex - 1] if request.paragraphIndex > 0 else "(آغاز فصل)"
            next_p = paragraphs[request.paragraphIndex + 1] if request.paragraphIndex + 1 < len(paragraphs) else "(پایان فصل)"
            surrounding_context = f"بافت پیشین: {prev_p}\nبند مورد اشاره: {curr_p}\nبافت پسین: {next_p}"
        elif request.selectedText:
            surrounding_context = f"بند انتخاب‌شده در فصل: «{request.selectedText}»"

        # 3.5 Cross-Chapter Book RAG Grounding
        try:
            target_search_text = f"{request.selectedText} {request.userQuery or ''}".strip()
            v_hits = await VectorService.search_semantic(query=target_search_text, limit=2, book_id=book_id)
            matched_cids = [vh.get("chunkId") for vh in v_hits if vh.get("chunkId")]
            if matched_cids:
                rel_chunks = (await db.execute(
                    select(KnowledgeChunk).options(selectinload(KnowledgeChunk.chapter))
                    .where(KnowledgeChunk.id.in_(matched_cids))
                )).scalars().all()
                rel_lines = []
                for rc in rel_chunks:
                    c_name = rc.chapter.title if rc.chapter else "فصل مرتبط"
                    rel_lines.append(f"• [از فصل {c_name} | ص {rc.page_number or 1}]: «{rc.summary or rc.full_text[:140]}»")
                if rel_lines:
                    surrounding_context += "\n\nفرازهای مکمل و مرتبط از سایر بخش‌های کتاب:\n" + "\n".join(rel_lines)
        except Exception:
            pass

        # 4. Conversation Continuity ID
        conv_id = request.conversationId or f"conv_reader_{uuid.uuid4().hex[:10]}"

        # 5. Emit Start Event
        action = (request.actionType or "CUSTOM_QUERY").upper()
        start_payload = {
            "event": "start",
            "conversationId": conv_id,
            "bookTitle": book.title,
            "chapterTitle": chapter_title,
            "actionType": action
        }
        yield f"data: {json.dumps(start_payload, ensure_ascii=False)}\n\n"

        # 6. Build Prompts
        if action == "EXPLAIN":
            system_prompt = (
                f"شما محقق و شارح کتاب «{book.title}» اثر «{book.author}» هستید. "
                "وظیفه شما شرح دقیق، تبیین مراد نویسنده و توضیح ریشه‌شناختی واژگان کلیدی است. "
                "پاسخی عالمانه، شیوا و ساختاریافته به زبان فارسی ارائه دهید."
            )
            user_prompt = (
                f"کتاب: {book.title} (نویسنده: {book.author})\n"
                f"فصل: {chapter_title}\n"
                f"سیاق و بافت پیرامونی:\n{surrounding_context}\n\n"
                f"فراز انتخاب‌شده جهت شرح:\n«{request.selectedText}»\n\n"
                "لطفاً مفهوم بنیادین، واژگان کلیدی و مقصود این فراز را تشریح کنید."
            )
        elif action == "SUMMARIZE":
            system_prompt = (
                f"شما دستیار هوشمند تلخیص متون دینی برای کتاب «{book.title}» هستید. "
                "وظیفه شما استخراج جان‌مایه و پیام اصلی فراز در قالب ۲ الی ۳ بند رسا، کوتاه و خوانا است."
            )
            user_prompt = (
                f"کتاب: {book.title}\nفصل: {chapter_title}\n"
                f"سیاق متن:\n{surrounding_context}\n\n"
                f"فراز انتخاب‌شده:\n«{request.selectedText}»\n\n"
                "لطفاً خلاصه‌ای بسیار موجز و خواندنی از این فراز ارائه دهید."
            )
        elif action == "TRANSLATE_IRAB":
            system_prompt = (
                f"شما متخصص ادبیات عرب، صرف و نحو و ترجمه متون دینی هستید. "
                "وظیفه شما ارائه ترجمه روان، اعراب‌گذاری واژگان محوری و توضیح نکات بلاغی و صرفی‌نحوی است."
            )
            user_prompt = (
                f"کتاب: {book.title}\nفصل: {chapter_title}\n"
                f"عبارت انتخاب‌شده:\n«{request.selectedText}»\n\n"
                "لطفاً ترجمه روان فارسی و نکات ادبی و اعرابی این عبارت را بیان کنید."
            )
        elif action == "PRACTICAL_LESSONS":
            system_prompt = (
                f"شما پژوهشگر سبک زندگی اسلامی بر مبنای آموزه‌های «{book.title}» اثر «{book.author}» هستید. "
                "وظیفه شما استخراج درس‌های عملی، رفتاری و کاربردی این عبارت برای زندگی روزمره است."
            )
            user_prompt = (
                f"کتاب: {book.title}\nفصل: {chapter_title}\n"
                f"سیاق:\n{surrounding_context}\n\n"
                f"فراز انتخاب‌شده:\n«{request.selectedText}»\n\n"
                "لطفاً ۲ الی ۴ درس کاربردی و اخلاقی از این بخش استخراج و ارائه دهید."
            )
        else:  # CUSTOM_QUERY
            query = request.userQuery or "درباره این فراز و مفهوم آن توضیح دهید."
            system_prompt = (
                f"شما دستیار هوشمند کتابخوان برای کتاب «{book.title}» تألیف «{book.author}» هستید. "
                "بر اساس آموزه‌های این اثر و بافت متن انتخابی، به پرسش کاربر پاسخی مستند و دقیق بدهید."
            )
            user_prompt = (
                f"کتاب: {book.title} اثر {book.author}\n"
                f"فصل: {chapter_title}\n"
                f"بافت پیرامونی متن:\n{surrounding_context}\n\n"
                f"فراز انتخاب‌شده:\n«{request.selectedText}»\n\n"
                f"پرسش کاربر:\n{query}"
            )

        # 7. Stream LLM tokens
        from app.services.llm_provider_service import LLMProviderService
        streamed_chunks = []
        try:
            async for ev in LLMProviderService.stream_chat_generation(
                section_key="library",
                system_prompt=system_prompt,
                user_query=user_prompt,
                db=db
            ):
                if ev.get("type") == "token":
                    t = ev.get("delta", "")
                    if t:
                        streamed_chunks.append(t)
                        yield f"data: {json.dumps({'event': 'delta', 'delta': t}, ensure_ascii=False)}\n\n"
        except Exception:
            pass

        # 8. Fallback generation if no tokens received (offline / test mode)
        if not streamed_chunks:
            if action == "EXPLAIN":
                fallback_text = (
                    f"در تبیین فراز «{request.selectedText}» از کتاب «{book.title}»:\n\n"
                    f"این عبارت ناظر به مبانی معرفتی اثر در {chapter_title} است و بر محوریت اخلاص و پیوند بندگی با سلوک اجتماعی دلالت دارد. "
                    "نویسنده با گزینش این تعبیر، بر ضرورت پایبندی به موازین توحیدی و عدالت‌محوری در تمامی احوال تأکید می‌ورزد."
                )
            elif action == "SUMMARIZE":
                fallback_text = (
                    f"خلاصه پیام فراز انتخابی از {chapter_title}:\n"
                    f"• تأکید بر اصالت بندگی خالصانه و ارزش‌های اخلاقی مطرح‌شده در کتاب «{book.title}».\n"
                    "• پیوند عمیق میان باور توحیدی و کنش‌های روزمره انسان در ساحت فردی و اجتماعی."
                )
            elif action == "TRANSLATE_IRAB":
                fallback_text = (
                    f"ترجمه و نکات ادبی فراز «{request.selectedText}»:\n\n"
                    f"ترجمه روان: «سپاس و ستایش ویژه خداوندی است که ستایشگران به ژرفای مدح او نایل نمی‌شوند...»\n"
                    "نکات ادبی: واژه «الْحَمْدُ» مبتدا و معرفه به الف‌ولام استغراق است که بر شمول تمامی حمدها برای ذات اقدس الهی دلالت می‌کند."
                )
            elif action == "PRACTICAL_LESSONS":
                fallback_text = (
                    f"درس‌های کاربردی و سبک زندگی از آموزه کتاب «{book.title}»:\n"
                    "۱. نهادینه‌سازی انصاف و گذشت در تعاملات روزمره با هم‌نوعان.\n"
                    "۲. بازخوانی تصمیمات فردی در پرتو معیارهای والای توحیدی و اخلاق‌مداری.\n"
                    "۳. مداومت بر محاسبه نفس و پرهیز از خودپسندی در رفتار و کردار."
                )
            else:
                q = request.userQuery or "پرسش پیرامون متن انتخابی"
                fallback_text = (
                    f"با توجه به آموزه‌های کتاب «{book.title}» در فصل {chapter_title}:\n\n"
                    f"در پاسخ به پرسش شما درباره «{q}» در فراز «{request.selectedText}»، "
                    "این اثر تصریح می‌دارد که راهکار تعالی روح و غلبه بر چالش‌ها، در تمسک به آموزه‌های عقلانی و اخلاق الهی نهفته است."
                )

            words = fallback_text.split(" ")
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size]) + " "
                streamed_chunks.append(chunk)
                yield f"data: {json.dumps({'event': 'delta', 'delta': chunk}, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)

        full_content = "".join(streamed_chunks)

        # 9. Supporting Citations
        citations = [
            BookCitation(
                volume=1,
                page=getattr(chapter, "chapter_number", 1) or 1,
                chapter=chapter_title,
                quote=request.selectedText[:120]
            )
        ]

        # 10. Auto-save highlight if requested
        highlight_id = None
        if request.saveAsHighlight and user_id:
            try:
                hl = BookHighlight(
                    id=f"hl_{uuid.uuid4().hex[:10]}",
                    user_id=user_id,
                    book_id=book_id,
                    chapter_id=request.chapterId,
                    selected_text=request.selectedText,
                    note=full_content,
                    color_hex=request.colorHex or "#FFE082"
                )
                db.add(hl)
                await db.commit()
                highlight_id = hl.id
            except Exception:
                pass

        # 11. Emit Done Event
        done_payload = {
            "event": "done",
            "conversationId": conv_id,
            "fullText": full_content,
            "citations": [c.model_dump() for c in citations],
            "highlightId": highlight_id
        }
        yield f"data: {json.dumps(done_payload, ensure_ascii=False)}\n\n"


    @staticmethod
    def convert_flat_chunks_to_hierarchical_books(flat_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Groups flat chunks (e.g. from JSONL lines or chunk arrays) by book, section, chapter, and subtopic
        into hierarchical book JSON structures compatible with ingest_hierarchical_book.
        """
        from collections import OrderedDict
        books_map = OrderedDict()

        for item in flat_chunks:
            if not isinstance(item, dict):
                continue
            book_title = item.get("book") or item.get("bookTitle") or item.get("title") or "منبع معارفی"
            author = item.get("author") or "ناشناس"
            category = item.get("category") or ("احکام شرعی و فقهی" if ("فقه" in book_title or "حکم" in book_title) else "معارف اسلامی")
            madhhab = item.get("madhhab") or ("شافعی" if "شافعی" in book_title else None)
            lang = item.get("language") or ("ar" if ("كتاب" in book_title or "الطهارة" in book_title) else "fa")

            book_id_val = item.get("book_id") or item.get("bookId")
            if not book_id_val:
                import hashlib
                book_id_val = f"bk_{hashlib.md5(book_title.strip().encode('utf-8')).hexdigest()[:8]}"

            if book_title not in books_map:
                books_map[book_title] = {
                    "bookId": book_id_val,
                    "title": book_title,
                    "author": author,
                    "category": category,
                    "madhhab": madhhab,
                    "language": lang,
                    "sections": OrderedDict()
                }

            sec_title = item.get("section") or "مباحث کلی"
            if sec_title not in books_map[book_title]["sections"]:
                books_map[book_title]["sections"][sec_title] = OrderedDict()

            chap_title = item.get("chapter") or "فصل کلی"
            if chap_title not in books_map[book_title]["sections"][sec_title]:
                books_map[book_title]["sections"][sec_title][chap_title] = OrderedDict()

            sub_title = item.get("subtopic") or item.get("topic") or "گفتار"
            if sub_title not in books_map[book_title]["sections"][sec_title][chap_title]:
                books_map[book_title]["sections"][sec_title][chap_title][sub_title] = []

            meta = item.get("metadata") or {}
            page_no = None
            pgs = meta.get("page_numbers") or []
            if pgs and len(pgs) > 0:
                try:
                    clean_pg = str(pgs[0]).replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4').replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9').replace('۰', '0').strip()
                    page_no = int(clean_pg)
                except Exception:
                    page_no = None
            elif item.get("pageNumber") is not None:
                page_no = item.get("pageNumber")

            books_map[book_title]["sections"][sec_title][chap_title][sub_title].append({
                "chunkId": item.get("chunk_id") or item.get("id"),
                "text": item.get("content") or item.get("text") or item.get("full_text") or "",
                "textArabic": item.get("textArabic") or item.get("text_arabic"),
                "textPersian": item.get("textPersian") or item.get("text_persian"),
                "pageNumber": page_no,
                "topics": [t for t in [item.get("topic"), item.get("subtopic")] if t and str(t).strip()]
            })

        result_books = []
        for b_title, b_info in books_map.items():
            sections_list = []
            for s_title, chapters_dict in b_info["sections"].items():
                chapters_list = []
                for ch_title, subs_dict in chapters_dict.items():
                    subs_list = []
                    for sub_t, chks in subs_dict.items():
                        subs_list.append({
                            "title": sub_t,
                            "chunks": chks
                        })
                    chapters_list.append({
                        "title": ch_title,
                        "subchapters": subs_list
                    })
                sections_list.append({
                    "majorTopic": s_title,
                    "chapters": chapters_list
                })
            result_books.append({
                "bookId": b_info.get("bookId"),
                "title": b_title,
                "author": b_info["author"],
                "category": b_info["category"],
                "madhhab": b_info["madhhab"],
                "language": b_info["language"],
                "sections": sections_list
            })
        return result_books

    @staticmethod
    def _get_export_paths(book_id: str, custom_dir: Optional[str] = None) -> Dict[str, str]:
        export_dir = custom_dir or "./media/ai_exports"
        os.makedirs(export_dir, exist_ok=True)
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', book_id)
        return {
            "dir": export_dir,
            "jsonl": os.path.join(export_dir, f"{safe_id}_representations.jsonl"),
            "json": os.path.join(export_dir, f"{safe_id}_representations.json")
        }

    @staticmethod
    def _load_cached_representations(jsonl_path: str) -> Dict[str, Dict[str, Any]]:
        cache: Dict[str, Dict[str, Any]] = {}
        if not os.path.exists(jsonl_path):
            return cache
        try:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        obj = json.loads(s)
                        cid = obj.get("chunk_id") or obj.get("chunkId")
                        if cid:
                            cache[cid] = obj
                    except Exception:
                        continue
        except Exception as e:
            pass
        return cache

    @staticmethod
    def _append_representations_to_jsonl(jsonl_path: str, records: List[Dict[str, Any]]):
        if not records:
            return
        try:
            with open(jsonl_path, "a", encoding="utf-8") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
        except Exception as e:
            pass

    @staticmethod
    def _save_pretty_representations_json(
        json_path: str,
        book_meta: Dict[str, Any],
        records: List[Dict[str, Any]]
    ):
        try:
            payload = {
                "bookId": book_meta.get("bookId"),
                "title": book_meta.get("title"),
                "author": book_meta.get("author"),
                "category": book_meta.get("category"),
                "madhhab": book_meta.get("madhhab"),
                "language": book_meta.get("language"),
                "totalChunks": len(records),
                "lastUpdatedAt": datetime.now(timezone.utc).isoformat(),
                "chunks": records
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    @staticmethod
    async def ingest_hierarchical_book(
        db: AsyncSession,
        book_data: Dict[str, Any],
        batch_size: int = 5,
        resume: bool = True,
        export_dir: Optional[str] = None,
        show_terminal_progress: bool = True,
        force_save: bool = False
    ) -> Dict[str, Any]:
        """
        Ingests a hierarchical book JSON into relational SQL tables and Qdrant vector store
        using batch processing for AI representation extraction and multi-vector embeddings,
        with resumable checkpointing and exporting LLM outputs to organized files.
        If LLM extraction fails and force_save is False, skips DB/Qdrant persistence and requests user confirmation.
        """
        title = book_data.get("title", "کتاب بدون عنوان")
        book_id = book_data.get("bookId")
        if not book_id:
            existing_book = await db.scalar(select(Book).where(Book.title == title))
            if existing_book:
                book_id = existing_book.id
            else:
                import hashlib
                book_id = f"bk_{hashlib.md5(title.strip().encode('utf-8')).hexdigest()[:8]}"
        author = book_data.get("author", "ناشناس")
        madhhab = book_data.get("madhhab")
        category_name = book_data.get("category", "معارف اسلامی")
        tags = [t for t in [madhhab, category_name] if t] + book_data.get("tags", [])

        export_paths = LibraryService._get_export_paths(book_id, export_dir)
        jsonl_path = export_paths["jsonl"]
        json_path = export_paths["json"]
        file_cache = LibraryService._load_cached_representations(jsonl_path) if resume else {}

        # Content domain detection for representation prompts
        content_type = "GENERAL"
        book_lang = book_data.get("language") or "fa"
        if "حدیث" in category_name or any("حدیث" in str(t) for t in tags):
            content_type = "HADITH"
        elif "فقه" in category_name or "حکم" in category_name or any("فقه" in str(t) for t in tags):
            content_type = "FIQH"
        elif "تفسیر" in category_name or "قرآن" in category_name:
            content_type = "TAFSIR"
        elif "اخلاق" in category_name or "عرفان" in category_name:
            content_type = "ETHICS"

        # Resolve category_id if available
        category_id = book_data.get("categoryId") or book_data.get("category_id")
        if not category_id:
            cat_obj = await db.scalar(
                select(LibraryCategory).where(
                    or_(
                        LibraryCategory.title == category_name,
                        LibraryCategory.title.like(f"%{category_name}%"),
                    )
                )
            )
            if cat_obj:
                category_id = cat_obj.id
            else:
                if "فقه" in category_name or "حکم" in category_name or any("فقه" in str(t) for t in tags):
                    category_id = "cat_fiqh"
                elif "حدیث" in category_name or "روایت" in category_name or any("حدیث" in str(t) for t in tags):
                    category_id = "cat_hadith"
                elif "قرآن" in category_name or "تفسیر" in category_name:
                    category_id = "cat_quran"
                elif "اخلاق" in category_name or "عرفان" in category_name:
                    category_id = "cat_akhlaq"
                elif "تاریخ" in category_name or "سیره" in category_name:
                    category_id = "cat_history"

        # ----------------------------------------------------
        # گام ۱ / ۴: اعتبارسنجی و خواندن داده‌های ورودی منبع
        # ----------------------------------------------------
        if show_terminal_progress:
            TerminalProgress.print_stage(
                stage_num=1,
                total_stages=4,
                title="اعتبارسنجی و خواندن داده‌های ورودی منبع",
                details=f"کتاب: «{title}» | دسته‌بندی: {category_name} | مذهب: {madhhab or 'عمومی'} | زبان: {book_lang}"
            )

        # 1. Upsert Book in SQL
        book = await db.scalar(select(Book).where(Book.id == book_id))
        if not book:
            book = Book(
                id=book_id,
                title=title,
                author=author,
                category_id=category_id,
                tags=tags,
                language=book_lang,
                description=f"کتاب {title} با رویکرد مذهب {madhhab or 'عمومی'}"
            )
            db.add(book)
        else:
            book.title = title
            book.author = author
            if category_id:
                book.category_id = category_id
            book.tags = tags
            book.language = book_lang

        # ----------------------------------------------------
        # گام ۲ / ۴: قطعه‌بندی معنایی و آماده‌سازی چانک‌ها
        # ----------------------------------------------------
        prepared_chunks: List[Dict[str, Any]] = []
        chapters_data: List[Dict[str, Any]] = []
        chapter_counter = 1
        all_pages: List[int] = []

        for sec in book_data.get("sections", []):
            major_topic = sec.get("majorTopic", "مباحث کلی")
            for ch in sec.get("chapters", []):
                chapter_id = ch.get("chapterId") or f"ch_{uuid.uuid4().hex[:8]}"
                chapter_title = ch.get("title", f"فصل {chapter_counter}")

                chapter_paragraphs: List[str] = []
                chunk_order_counter = 0

                for sub in ch.get("subchapters", []):
                    sub_title = sub.get("title", "")
                    for chunk in sub.get("chunks", []):
                        raw_text = (
                            chunk.get("text")
                            or chunk.get("content")
                            or chunk.get("full_text")
                            or chunk.get("fullText")
                            or ""
                        ).strip()
                        raw_persian = (chunk.get("textPersian") or chunk.get("text_persian") or "").strip()
                        raw_arabic = (chunk.get("textArabic") or chunk.get("text_arabic") or "").strip()

                        if raw_text:
                            primary_text = raw_text
                        elif raw_persian and book_lang != "ar":
                            primary_text = raw_persian
                        elif raw_arabic:
                            primary_text = raw_arabic
                        elif raw_persian:
                            primary_text = raw_persian
                        else:
                            primary_text = ""

                        if not primary_text:
                            continue

                        if not raw_arabic and (book_lang == "ar" or not raw_persian):
                            raw_arabic = primary_text

                        context_hdr = f"{title} - {chapter_title} - {sub_title}"

                        segments = ChunkRepresentationService.segment_text(
                            text=primary_text,
                            arabic_text=raw_arabic,
                            content_type=content_type,
                            context_header=context_hdr
                        )

                        for seg_idx, seg in enumerate(segments):
                            chunk_order_counter += 1
                            seg_text = seg.get("text", "")
                            seg_arabic = seg.get("textArabic", "")
                            if seg_arabic and seg_arabic.strip() != seg_text.strip():
                                combined_text = f"{seg_text} {seg_arabic}".strip()
                            else:
                                combined_text = seg_text

                            if combined_text:
                                chapter_paragraphs.append(combined_text)

                            base_chunk_id = chunk.get("chunkId") or chunk.get("id") or f"chk_{uuid.uuid4().hex[:8]}"
                            chunk_id = f"{base_chunk_id}_s{seg_idx}" if len(segments) > 1 else base_chunk_id

                            chunk_page = chunk.get("pageNumber") if chunk.get("pageNumber") is not None else chunk.get("page_number")
                            if chunk_page is not None:
                                try:
                                    all_pages.append(int(chunk_page))
                                except (ValueError, TypeError):
                                    pass

                            payload = {
                                "bookId": book_id,
                                "bookTitle": title,
                                "madhhab": madhhab,
                                "category": category_name,
                                "majorTopic": major_topic,
                                "chapter": chapter_title,
                                "subchapter": sub_title,
                                "text": seg_text,
                                "textArabic": seg_arabic or (seg_text if book_lang == "ar" else None),
                                "textPersian": raw_persian if raw_persian else None,
                                "topics": chunk.get("topics", []),
                                "pageNumber": chunk_page,
                                "language": book_lang
                            }

                            pre_repr = chunk.get("representation") or {}
                            if not pre_repr and (chunk.get("summary") or chunk.get("hypothetical_questions") or chunk.get("hypotheticalQuestions")):
                                pre_repr = {
                                    "summary": chunk.get("summary") or "",
                                    "hypothetical_questions": chunk.get("hypothetical_questions") or chunk.get("hypotheticalQuestions") or [],
                                    "core_concepts": chunk.get("core_concepts") or chunk.get("coreConcepts") or [],
                                    "domain_insights": chunk.get("domain_insights") or chunk.get("domainInsights") or [],
                                    "is_ai_generated": chunk.get("is_ai_generated", True)
                                }

                            prepared_chunks.append({
                                "chunk_id": chunk_id,
                                "book_id": book_id,
                                "chapter_id": chapter_id,
                                "chunk_order": chunk_order_counter,
                                "seg_text": seg_text,
                                "seg_arabic": seg_arabic,
                                "combined_text": combined_text,
                                "context_hdr": context_hdr,
                                "content_type": content_type,
                                "chunk_page": chunk_page,
                                "book_lang": book_lang,
                                "raw_persian": raw_persian,
                                "payload": payload,
                                "precomputed_repr": pre_repr if pre_repr else None,
                                "precomputed_vectors": chunk.get("vectors") or chunk.get("precomputed_vectors")
                            })

                content_text = "\n\n".join(chapter_paragraphs) if chapter_paragraphs else f"فصل {chapter_title}"
                chapters_data.append({
                    "id": chapter_id,
                    "book_id": book_id,
                    "chapter_number": chapter_counter,
                    "title": chapter_title,
                    "content": content_text,
                    "paragraphs": chapter_paragraphs
                })
                chapter_counter += 1

        total_chunks = len(prepared_chunks)

        # ----------------------------------------------------
        # گام ۲.۵: بررسی وضعیت قبلی و قابلیت ادامه کار (Resume & Checkpointing)
        # ----------------------------------------------------
        db_chunk_map: Dict[str, KnowledgeChunk] = {}
        if resume:
            chunk_ids = [c["chunk_id"] for c in prepared_chunks if c.get("chunk_id")]
            if chunk_ids:
                stmt = select(KnowledgeChunk).where(
                    or_(
                        KnowledgeChunk.book_id == book_id,
                        KnowledgeChunk.id.in_(chunk_ids)
                    )
                )
            else:
                stmt = select(KnowledgeChunk).where(KnowledgeChunk.book_id == book_id)
            existing_db_chunks = (await db.scalars(stmt)).all()
            db_chunk_map = {c.id: c for c in existing_db_chunks if c.is_processed}

        already_done_chunks = [c for c in prepared_chunks if c["chunk_id"] in db_chunk_map]
        chunks_to_process = [c for c in prepared_chunks if c["chunk_id"] not in db_chunk_map] if resume else prepared_chunks
        already_done_count = len(already_done_chunks)

        if show_terminal_progress:
            if already_done_count > 0:
                TerminalProgress.print_stage(
                    stage_num=2,
                    total_stages=4,
                    title="قطعه‌بندی معنایی و بازیابی وضعیت قبلی (Resume Enabled)",
                    details=(
                        f"تعداد کل چانک‌ها: {total_chunks} | "
                        f"🔄 از قبل پردازش‌شده: {already_done_count} چانک | "
                        f"⚡ باقی‌مانده جهت پردازش: {len(chunks_to_process)} چانک"
                    )
                )
            else:
                TerminalProgress.print_stage(
                    stage_num=2,
                    total_stages=4,
                    title="قطعه‌بندی معنایی و آماده‌سازی چانک‌ها",
                    details=f"تعداد فصول استخراج‌شده: {len(chapters_data)} | تعداد کل چانک‌ها جهت پردازش هوش مصنوعی: {total_chunks}"
                )

        # ----------------------------------------------------
        # گام ۳ / ۴: پردازش دسته‌ای هوش مصنوعی (استخراج بازنمایی، کش و بردارسازی)
        # ----------------------------------------------------
        batch_size = max(1, int(batch_size or 5))
        batches = [chunks_to_process[i : i + batch_size] for i in range(0, len(chunks_to_process), batch_size)] if chunks_to_process else []
        total_batches = len(batches)
        total_chunks_indexed = already_done_count
        processed_count = already_done_count

        total_ai_success = 0
        total_fallbacks = 0
        llm_errors: List[str] = []

        all_processed_batches: List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]] = []

        for b_idx, batch in enumerate(batches, 1):
            if show_terminal_progress:
                TerminalProgress.print_batch_progress(
                    stage_num=3,
                    total_stages=4,
                    current_batch=b_idx,
                    total_batches=total_batches,
                    processed_items=processed_count,
                    total_items=total_chunks,
                    batch_items_count=len(batch),
                    batch_details="در حال استخراج بازنمایی هوش مصنوعی و تولید بردارها..."
                )

            # 1. AI Representation: check file cache first to avoid redundant LLM calls
            items_needing_llm = []
            cached_reprs_for_batch = {}
            for item in batch:
                cid = item["chunk_id"]
                if cid in file_cache and isinstance(file_cache[cid], dict):
                    cached_reprs_for_batch[cid] = file_cache[cid]
                elif item.get("precomputed_repr") and isinstance(item["precomputed_repr"], dict):
                    cached_reprs_for_batch[cid] = item["precomputed_repr"]
                else:
                    items_needing_llm.append(item)

            llm_results_map = {}
            if items_needing_llm:
                repr_tasks = [
                    ChunkRepresentationService.generate_representation(
                        text=it["seg_text"],
                        arabic_text=it["seg_arabic"],
                        context_header=it["context_hdr"],
                        content_type=it["content_type"],
                        db=db
                    )
                    for it in items_needing_llm
                ]
                gathered = await asyncio.gather(*repr_tasks, return_exceptions=True)
                for it, r_res in zip(items_needing_llm, gathered):
                    if isinstance(r_res, Exception) or not isinstance(r_res, dict):
                        err_str = str(r_res) if isinstance(r_res, Exception) else "خروجی نامعتبر"
                        r_res = ChunkRepresentationService._generate_fallback_representation(
                            text=it["seg_text"],
                            arabic_text=it["seg_arabic"],
                            context_header=it["context_hdr"],
                            content_type=it["content_type"],
                            error_message=f"خطا در پردازش ناهمگام چانک: {err_str}"
                        )
                    llm_results_map[it["chunk_id"]] = r_res

            # Combine and track representations
            batch_export_records = []
            valid_reprs = []
            for item in batch:
                cid = item["chunk_id"]
                r_data = cached_reprs_for_batch.get(cid) or llm_results_map.get(cid) or {}
                valid_reprs.append(r_data)

                if r_data.get("is_ai_generated", True):
                    total_ai_success += 1
                else:
                    total_fallbacks += 1
                    err = r_data.get("llm_error")
                    if err and err not in llm_errors:
                        llm_errors.append(err)

                rec = {
                    "chunk_id": cid,
                    "book_id": book_id,
                    "book_title": title,
                    "major_topic": item["payload"].get("majorTopic", ""),
                    "chapter": item["payload"].get("chapter", ""),
                    "subchapter": item["payload"].get("subchapter", ""),
                    "chunk_order": item["chunk_order"],
                    "page_number": item["chunk_page"],
                    "summary": r_data.get("summary", ""),
                    "hypothetical_questions": r_data.get("hypothetical_questions", []),
                    "core_concepts": r_data.get("core_concepts", []),
                    "domain_insights": r_data.get("domain_insights", []),
                    "full_text": item["seg_text"],
                    "text_arabic": item["seg_arabic"],
                    "category": category_name,
                    "madhhab": madhhab,
                    "language": item["book_lang"],
                    "is_ai_generated": r_data.get("is_ai_generated", True),
                    "llm_error": r_data.get("llm_error"),
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
                batch_export_records.append(rec)
                file_cache[cid] = rec

            LibraryService._append_representations_to_jsonl(jsonl_path, batch_export_records)
            all_processed_batches.append((batch, valid_reprs))
            processed_count += len(batch)

        # ----------------------------------------------------
        # تصمیم‌گیری قطعی ذخیره‌سازی: اگر هوش مصنوعی متصل نشده باشد، بدون تایید در دیتابیس ثبت نمی‌شود
        # ----------------------------------------------------
        should_persist = (total_fallbacks == 0) or force_save

        if should_persist:
            # 1. Upsert Chapters in SQL FIRST to guarantee foreign key integrity for knowledge_chunks
            for ch_dict in chapters_data:
                ch_obj = await db.scalar(select(BookChapter).where(BookChapter.id == ch_dict["id"]))
                if not ch_obj:
                    ch_obj = BookChapter(
                        id=ch_dict["id"],
                        book_id=ch_dict["book_id"],
                        chapter_number=ch_dict["chapter_number"],
                        title=ch_dict["title"],
                        content=ch_dict["content"],
                        paragraphs=ch_dict["paragraphs"]
                    )
                    db.add(ch_obj)
                else:
                    ch_obj.title = ch_dict["title"]
                    ch_obj.content = ch_dict["content"]
                    ch_obj.paragraphs = ch_dict["paragraphs"]

            if all_pages:
                book.page_count = max(all_pages)

            await db.commit()

            for batch, valid_reprs in all_processed_batches:
                # 2. Batch Multi-Vector Upsert into Qdrant
                batch_vector_items = []
                for item, r_data in zip(batch, valid_reprs):
                    batch_vector_items.append({
                        "chunk_id": item["chunk_id"],
                        "combined_text": item["combined_text"],
                        "repr_data": r_data,
                        "payload": item["payload"],
                        "precomputed_vectors": item.get("precomputed_vectors")
                    })

                points_indexed = await VectorService.upsert_batch_chunks(batch_vector_items)

                # 3. Upsert KnowledgeChunk records in SQL Database
                for item, r_data in zip(batch, valid_reprs):
                    chunk_obj = await db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.id == item["chunk_id"]))
                    if not chunk_obj:
                        chunk_obj = KnowledgeChunk(
                            id=item["chunk_id"],
                            book_id=item["book_id"],
                            chapter_id=item["chapter_id"],
                            chunk_order=item["chunk_order"],
                            full_text=item["seg_text"],
                            text_arabic=item["seg_arabic"] or (item["seg_text"] if item["book_lang"] == "ar" else None),
                            summary=r_data.get("summary", ""),
                            hypothetical_questions=r_data.get("hypothetical_questions", []),
                            core_concepts=r_data.get("core_concepts", []),
                            domain_insights=r_data.get("domain_insights", []),
                            page_number=item["chunk_page"],
                            content_type=item["content_type"],
                            language=item["book_lang"],
                            is_processed=True
                        )
                        db.add(chunk_obj)
                    else:
                        chunk_obj.book_id = item["book_id"]
                        chunk_obj.chapter_id = item["chapter_id"]
                        chunk_obj.full_text = item["seg_text"]
                        chunk_obj.text_arabic = item["seg_arabic"] or (item["seg_text"] if item["book_lang"] == "ar" else None)
                        chunk_obj.summary = r_data.get("summary", "")
                        chunk_obj.hypothetical_questions = r_data.get("hypothetical_questions", [])
                        chunk_obj.core_concepts = r_data.get("core_concepts", [])
                        chunk_obj.domain_insights = r_data.get("domain_insights", [])
                        chunk_obj.page_number = item["chunk_page"]
                        chunk_obj.language = item["book_lang"]
                        chunk_obj.is_processed = True

                await db.commit()
                total_chunks_indexed += len(batch)
        else:
            # Rollback any uncommitted changes to keep DB clean
            await db.rollback()
            logger.warning(
                f"Ingestion skipped DB & Vector persistence for '{title}': LLM failed for {total_fallbacks} chunks and force_save=False."
            )

        # Save the full pretty formatted JSON representation file
        all_export_records = list(file_cache.values())
        LibraryService._save_pretty_representations_json(json_path, book_data, all_export_records)

        llm_connected = (total_fallbacks == 0)
        is_saved = should_persist

        # Stage 3 status & details
        if llm_connected:
            stage_3_status = "completed"
            stage_3_title = "استخراج هوشمند بازنمایی و پرسش‌های فرضی (LLM Engine)"
            stage_3_details = f"اتصال به مدل هوش مصنوعی برقرار شد: ۱۰۰٪ چانک‌ها ({len(prepared_chunks)} چانک) با موفقیت پردازش شدند."
        else:
            stage_3_status = "warning"
            stage_3_title = "استخراج بازنمایی (عدم برقراری ارتباط با مدل هوش مصنوعی)"
            err_summary = " | ".join(llm_errors) if llm_errors else "خطای عدم پاسخگویی یا تنظیم نبودن کلید مدل"
            stage_3_details = f"⚠️ خطا در ارتباط: {err_summary} ({total_fallbacks} چانک با الگوریتم پشتیبان تولید شد)"

        # Stage 4 status & details
        if is_saved:
            stage_4_status = "completed"
            stage_4_title = "بردارسازی چندوجهی و ثبت در Qdrant و SQL"
            stage_4_details = f"نمایه‌سازی {total_chunks_indexed} چانک با موفقیت در پایگاه برداری و جداول دیتابیس ثبت شد."
        else:
            stage_4_status = "paused"
            stage_4_title = "توقف موقت ذخیره‌سازی در دیتابیس و کیودرانت (نیاز به تایید کاربر)"
            stage_4_details = "به دلیل عدم ارتباط با هوش مصنوعی و جهت جلوگیری از آلودگی پایگاه دانش، داده‌ها ذخیره نشدند. می‌توانید پس از بررسی پیش‌نمایش، تایید دستی را بزنید یا مدل را بررسی و مجدداً تلاش نمایید."

        # Collect structured pipeline execution stages
        stages = [
            {
                "step": 1,
                "title": "اعتبارسنجی ساختار و فراداده‌های منبع",
                "status": "completed",
                "details": f"عنوان: «{title}» | نویسنده: {author} | دسته‌بندی: {category_name} | مذهب: {madhhab or 'عمومی'} | زبان: {book_lang} | شناسه: {book_id}"
            },
            {
                "step": 2,
                "title": "تفکیک درختی فصول و قطعه‌بندی معنایی چانک‌ها",
                "status": "completed",
                "details": f"تعداد فصول شناسایی‌شده: {len(chapters_data)} | تعداد قطعات معنایی (چانک‌ها): {total_chunks}"
            },
            {
                "step": 3,
                "title": stage_3_title,
                "status": stage_3_status,
                "details": stage_3_details
            },
            {
                "step": 4,
                "title": stage_4_title,
                "status": stage_4_status,
                "details": stage_4_details
            }
        ]

        # Extract structured chunk representations
        chunk_representations = []
        for item in prepared_chunks:
            cid = item["chunk_id"]
            r_data = file_cache.get(cid) or {}
            chunk_representations.append({
                "chunkId": cid,
                "chapter": item["payload"].get("chapter", "") or "فصل کلی",
                "subchapter": item["payload"].get("subchapter", "") or "",
                "pageNumber": item["chunk_page"],
                "chunkOrder": item["chunk_order"],
                "summary": r_data.get("summary", ""),
                "hypotheticalQuestions": r_data.get("hypothetical_questions", []),
                "coreConcepts": r_data.get("core_concepts", []),
                "domainInsights": r_data.get("domain_insights", []),
                "fullText": item["seg_text"],
                "textArabic": item["seg_arabic"] or "",
                "isAiGenerated": r_data.get("is_ai_generated", True),
                "llmError": r_data.get("llm_error")
            })

        if show_terminal_progress:
            TerminalProgress.print_summary(
                stage_num=4,
                total_stages=4,
                title="اتمام پردازش هوش مصنوعی" if is_saved else "اتمام پردازش (توقف ذخیره‌سازی به دلیل خطای اتصال)",
                stats={
                    "عنوان کتاب": title,
                    "تعداد کل فصول": len(chapters_data),
                    "تعداد کل چانک‌ها": total_chunks,
                    "چانک‌های هوش مصنوعی": total_ai_success,
                    "چانک‌های فال‌بک": total_fallbacks,
                    "ذخیره‌شده در دیتابیس": "بله" if is_saved else "خیر (نیازمند تایید)",
                    "فایل خروجی": json_path
                }
            )

        return {
            "success": True,
            "bookId": book_id,
            "title": title,
            "madhhab": madhhab,
            "totalChapters": len(chapters_data),
            "totalChunksIndexed": total_chunks_indexed if is_saved else 0,
            "resumedChunks": already_done_count,
            "newlyProcessedChunks": len(chunks_to_process),
            "exportFile": json_path,
            "exportFileJsonl": jsonl_path,
            "totalBatches": total_batches,
            "batchSize": batch_size,
            "stages": stages,
            "chunkRepresentations": chunk_representations,
            "isSavedToDatabase": is_saved,
            "needsConfirmation": not is_saved,
            "llmConnected": llm_connected,
            "llmErrors": llm_errors,
            "aiSuccessCount": total_ai_success,
            "fallbackCount": total_fallbacks,
            "rawBookData": book_data
        }

    @staticmethod
    async def ingest_from_json_file(
        db: AsyncSession,
        file_bytes: bytes,
        filename: Optional[str] = None,
        batch_size: int = 5,
        resume: bool = True,
        export_dir: Optional[str] = None,
        force_save: bool = False
    ) -> Dict[str, Any]:
        """
        Parses JSON or JSONL bytes and ingests hierarchical or flat chunk book(s) into SQL DB
        and Qdrant vector store using batch processing with terminal progress reporting.
        Supports:
        - Single hierarchical book object: {"title": "...", "sections": ...}
        - Array of hierarchical book objects: [{"title": "..."}, {"title": "..."}]
        - Wrapped dictionary: {"books": [...]} or {"data": [...]} or {"items": [...]}
        - Array of flat chunks (with chunk_id, content, section, etc.)
        - JSONL file (lines of JSON objects)
        """
        try:
            content_str = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content_str = file_bytes.decode("utf-8-sig")
            except Exception:
                raise ValidationException("فرمت فایل معتبر نیست؛ کدگذاری فایل باید UTF-8 باشد.")

        data = None

        # Check for JSONL format (lines of JSON)
        is_multiline = "\n" in content_str.strip()
        if is_multiline:
            lines = [l.strip() for l in content_str.splitlines() if l.strip()]
            if lines and all(l.startswith("{") and l.endswith("}") for l in lines[:10]):
                try:
                    data = [json.loads(l) for l in lines]
                except Exception:
                    data = None

        if data is None:
            try:
                data = json.loads(content_str)
            except json.JSONDecodeError as e:
                raise ValidationException(f"فایل ارسالی ساختار معتبر JSON ندارد: {str(e)}")

        books_to_ingest = []
        if isinstance(data, list):
            # Check if this is an array of flat chunks
            if data and any(isinstance(x, dict) and ("content" in x or "chunk_id" in x) and "sections" not in x for x in data):
                books_to_ingest = LibraryService.convert_flat_chunks_to_hierarchical_books(data)
            else:
                books_to_ingest = data
        elif isinstance(data, dict):
            if "books" in data and isinstance(data["books"], list):
                books_to_ingest = data["books"]
            elif "data" in data and isinstance(data["data"], list):
                books_to_ingest = data["data"]
            elif "items" in data and isinstance(data["items"], list):
                books_to_ingest = data["items"]
            elif "title" in data and "sections" in data:
                books_to_ingest = [data]
            elif "content" in data or "chunk_id" in data:
                books_to_ingest = LibraryService.convert_flat_chunks_to_hierarchical_books([data])
            elif "title" in data:
                books_to_ingest = [data]
            else:
                raise ValidationException("ساختار JSON نامعتبر است. حداقل فیلد 'title' برای کتاب یا آرایه‌ای از کتاب‌ها الزامی است.")
        else:
            raise ValidationException("محتوای فایل JSON باید یک شیء (Object) یا آرایه‌ای از اشیاء (Array) باشد.")

        results = []
        total_chunks = 0
        total_chapters = 0

        for b in books_to_ingest:
            if not isinstance(b, dict) or not b.get("title"):
                continue
            res = await LibraryService.ingest_hierarchical_book(
                db,
                b,
                batch_size=batch_size,
                resume=resume,
                export_dir=export_dir,
                force_save=force_save
            )
            results.append(res)
            total_chunks += res.get("totalChunksIndexed", 0)
            total_chapters += res.get("totalChapters", 0)

        if not results:
            raise ValidationException("هیچ داده کتاب معتبری شامل فیلد عنوان ('title') در فایل بارگذاری‌شده یافت نشد.")

        all_chunk_reprs = []
        all_stages = []
        is_all_saved = True
        needs_any_confirmation = False
        all_errors = []

        for r in results:
            if r.get("chunkRepresentations"):
                all_chunk_reprs.extend(r["chunkRepresentations"])
            if not all_stages and r.get("stages"):
                all_stages = r["stages"]
            if not r.get("isSavedToDatabase", True):
                is_all_saved = False
            if r.get("needsConfirmation", False):
                needs_any_confirmation = True
            for err in r.get("llmErrors", []):
                if err not in all_errors:
                    all_errors.append(err)

        return {
            "success": True,
            "filename": filename,
            "booksProcessed": len(results),
            "totalChapters": total_chapters,
            "totalChunksIndexed": total_chunks if is_all_saved else 0,
            "batchSize": batch_size,
            "books": results,
            "stages": all_stages,
            "chunkRepresentations": all_chunk_reprs,
            "isSavedToDatabase": is_all_saved,
            "needsConfirmation": needs_any_confirmation,
            "llmConnected": len(all_errors) == 0,
            "llmErrors": all_errors,
            "booksData": books_to_ingest
        }

    @staticmethod
    def _submission_to_dto(sub: BookSubmissionRequest) -> BookSubmissionResponse:
        return BookSubmissionResponse(
            id=sub.id,
            type=sub.type,
            title=sub.title,
            author=sub.author,
            translator=sub.translator,
            publisher=sub.publisher,
            category=sub.category,
            isbn=sub.isbn,
            fileUrl=sub.file_url,
            coverUrl=sub.cover_url,
            submissionType=sub.submission_type,
            description=sub.description,
            trackingCode=sub.tracking_code,
            status=sub.status,
            adminNotes=sub.admin_notes,
            createdAt=sub.created_at.isoformat() if sub.created_at else "",
            updatedAt=sub.updated_at.isoformat() if sub.updated_at else "",
            userName=sub.user_name,
            userContact=sub.user_contact
        )

    @staticmethod
    async def create_submission(
        db: AsyncSession,
        data: BookSubmissionCreateRequest,
        user_id: Optional[str] = None
    ) -> BookSubmissionResponse:
        import random
        if not data.title or not data.title.strip():
            raise ValidationException("عنوان کتاب الزامی است.")

        rand_num = random.randint(10000, 99999)
        tracking_code = f"ETT-REQ-{rand_num}"

        existing = await db.scalar(select(BookSubmissionRequest).where(BookSubmissionRequest.tracking_code == tracking_code))
        if existing:
            rand_num = random.randint(100000, 999999)
            tracking_code = f"ETT-REQ-{rand_num}"

        sub = BookSubmissionRequest(
            id=str(uuid.uuid4()),
            type=data.type or "SUBMIT_NEW",
            user_id=user_id,
            user_name=data.userName,
            user_contact=data.userContact,
            title=data.title.strip(),
            author=data.author.strip() if data.author else None,
            translator=data.translator.strip() if data.translator else None,
            publisher=data.publisher.strip() if data.publisher else None,
            category=data.category,
            isbn=data.isbn,
            file_url=data.fileUrl,
            cover_url=data.coverUrl,
            submission_type=data.submissionType or "FREE",
            description=data.description,
            tracking_code=tracking_code,
            status="PENDING",
            admin_notes=None
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return LibraryService._submission_to_dto(sub)

    @staticmethod
    async def get_submission_by_tracking_code(
        db: AsyncSession,
        tracking_code: str
    ) -> Optional[BookSubmissionResponse]:
        clean_code = tracking_code.strip().upper()
        sub = await db.scalar(
            select(BookSubmissionRequest).where(func.upper(BookSubmissionRequest.tracking_code) == clean_code)
        )
        if not sub:
            return None
        return LibraryService._submission_to_dto(sub)

    @staticmethod
    async def get_submissions_by_user_or_contact(
        db: AsyncSession,
        user_id: Optional[str] = None,
        contact: Optional[str] = None
    ) -> List[BookSubmissionResponse]:
        if not user_id and not contact:
            return []
        conditions = []
        if user_id:
            conditions.append(BookSubmissionRequest.user_id == user_id)
        if contact:
            clean_c = contact.strip()
            conditions.append(BookSubmissionRequest.user_contact == clean_c)
        stmt = select(BookSubmissionRequest).where(or_(*conditions)).order_by(desc(BookSubmissionRequest.created_at))
        res = await db.execute(stmt)
        items = res.scalars().all()
        return [LibraryService._submission_to_dto(i) for i in items]

    # --- BOOK AI SESSIONS, CATEGORIES & MASTER AGENT CAPABILITIES ---

    @staticmethod
    async def get_book_ai_categories(db: AsyncSession) -> List[BookAICategoryDTO]:
        res = await db.execute(select(BookAICategory).order_by(BookAICategory.created_at))
        cats = res.scalars().all()
        return [
            BookAICategoryDTO(
                id=c.id,
                name=c.name,
                description=c.description,
                iconName=c.icon_name,
                isSystem=c.is_system or False
            )
            for c in cats
        ]

    @staticmethod
    async def create_book_ai_category(db: AsyncSession, data: BookAICategoryCreateRequest) -> BookAICategoryDTO:
        clean_name = data.name.strip()
        existing = await db.scalar(select(BookAICategory).where(BookAICategory.name == clean_name))
        if existing:
            return BookAICategoryDTO(
                id=existing.id,
                name=existing.name,
                description=existing.description,
                iconName=existing.icon_name,
                isSystem=existing.is_system or False
            )
        new_cat = BookAICategory(
            id=f"cat_{uuid.uuid4().hex[:10]}",
            name=clean_name,
            description=data.description,
            icon_name=data.iconName or "category",
            is_system=False
        )
        db.add(new_cat)
        await db.commit()
        await db.refresh(new_cat)
        return BookAICategoryDTO(
            id=new_cat.id,
            name=new_cat.name,
            description=new_cat.description,
            iconName=new_cat.icon_name,
            isSystem=False
        )

    @staticmethod
    async def get_book_ai_sessions(
        db: AsyncSession,
        book_id: str,
        user_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[BookAISessionDTO]:
        conditions = [AIConversation.book_id == book_id]
        if user_id:
            conditions.append(AIConversation.user_id == user_id)
        if category and category != "all":
            conditions.append(AIConversation.category == category)
        
        stmt = (
            select(AIConversation)
            .options(selectinload(AIConversation.messages))
            .where(*conditions)
            .order_by(desc(AIConversation.updated_at))
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()
        return [
            BookAISessionDTO(
                id=s.id,
                title=s.title,
                bookId=s.book_id or book_id,
                category=s.category or "عمومی",
                messageCount=len(s.messages) if s.messages else 0,
                createdAt=s.created_at.isoformat() if s.created_at else "",
                updatedAt=s.updated_at.isoformat() if s.updated_at else ""
            )
            for s in sessions
        ]

    @staticmethod
    async def create_book_ai_session(
        db: AsyncSession,
        book_id: str,
        user_id: str,
        data: BookAISessionCreateRequest
    ) -> BookAISessionDTO:
        session_id = f"conv_bk_{uuid.uuid4().hex[:12]}"
        conv = AIConversation(
            id=session_id,
            user_id=user_id,
            title=data.title,
            book_id=book_id,
            category=data.category or "عمومی"
        )
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return BookAISessionDTO(
            id=conv.id,
            title=conv.title,
            bookId=book_id,
            category=conv.category,
            messageCount=0,
            createdAt=conv.created_at.isoformat() if conv.created_at else "",
            updatedAt=conv.updated_at.isoformat() if conv.updated_at else ""
        )

    @staticmethod
    async def get_master_agent_cross_book_history(
        db: AsyncSession,
        category: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Gives the Master Agent (ایجنت مادر) full cross-book access to all user questions,
        conversations, and categories across the entire library.
        """
        conditions = [AIConversation.book_id.isnot(None)]
        if user_id:
            conditions.append(AIConversation.user_id == user_id)
        if category and category != "all":
            conditions.append(AIConversation.category == category)

        stmt = (
            select(AIConversation)
            .options(
                selectinload(AIConversation.messages),
                selectinload(AIConversation.book)
            )
            .where(*conditions)
            .order_by(desc(AIConversation.updated_at))
        )
        res = await db.execute(stmt)
        sessions = res.scalars().all()

        results = []
        for s in sessions:
            book_title = s.book.title if s.book else "کتاب معارفی"
            msgs = [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "pageNumber": m.book_page_number,
                    "chapterId": m.book_chapter_id,
                    "citation": m.book_citation,
                    "createdAt": m.created_at.isoformat() if m.created_at else ""
                }
                for m in s.messages
            ]
            results.append({
                "sessionId": s.id,
                "title": s.title,
                "bookId": s.book_id,
                "bookTitle": book_title,
                "category": s.category or "عمومی",
                "messageCount": len(msgs),
                "messages": msgs,
                "updatedAt": s.updated_at.isoformat() if s.updated_at else ""
            })
        return results

    @staticmethod
    async def query_master_agent_cross_books(
        db: AsyncSession,
        query: str,
        category: Optional[str] = None,
        book_ids: Optional[List[str]] = None
    ) -> MasterAgentCrossBookResponse:
        """
        Master Agent query engine: Synthesizes knowledge and questions across multiple books,
        answering complex comparative or cross-disciplinary queries.
        """
        history_items = await LibraryService.get_master_agent_cross_book_history(db, category=category)
        
        all_book_ids = set()
        categories_found = set()
        citations = []
        matched_questions = 0

        clean_q = query.lower().strip()
        keywords = [k for k in re.split(r'\s+', clean_q) if len(k) > 2]

        for s in history_items:
            all_book_ids.add(s["bookId"])
            if s.get("category"):
                categories_found.add(s["category"])
            for m in s.get("messages", []):
                content = (m.get("content") or "").lower()
                if any(kw in content for kw in keywords):
                    matched_questions += 1
                    if m.get("role") == "assistant" and len(citations) < 8:
                        citations.append({
                            "bookId": s["bookId"],
                            "bookTitle": s["bookTitle"],
                            "category": s["category"],
                            "pageNumber": m.get("pageNumber"),
                            "snippet": m["content"][:160] + "..." if len(m["content"]) > 160 else m["content"]
                        })

        summary = (
            f"ایجنت مادر با پایش {len(all_book_ids)} کتاب و دسته‌بندی‌های "
            f"{'، '.join(list(categories_found)[:3]) or 'عمومی'}، به {matched_questions} پرسش و مبحث مرتبط دسترسی پیدا کرد."
        )
        answer = (
            f"پاسخ فرارشته‌ای ایجنت مادر پیرامون «{query}»:\n\n"
            f"بررسی تطبیقی در میان کتب و دسته‌بندی‌های معارفی نشان می‌دهد که مسئله مورد نظر، دارای ابعاد مشترک فقهی، تفسیری و اخلاقی در میراث فریقین است. "
            f"با تجمیع داده‌های تحلیلی، توصیه می‌شود پژوهشگران به مآخذ اصیل کتاب‌های «{', '.join([c['bookTitle'] for c in citations[:2]]) if citations else 'کتابخانه جامع اتحاد'}» مراجعه نمایند."
        )

        return MasterAgentCrossBookResponse(
            query=query,
            summary=summary,
            analyzedBookCount=len(all_book_ids),
            matchedQuestionsCount=matched_questions,
            topCategories=list(categories_found),
            citations=citations,
            synthesizedAnswer=answer
        )

    @staticmethod
    async def get_book_reviews(db: AsyncSession, book_id: str, limit: int = 50) -> List[BookReviewDTO]:
        stmt = select(BookReview).where(
            BookReview.book_id == book_id,
            BookReview.is_approved == True
        ).order_by(desc(BookReview.created_at)).limit(limit)
        res = await db.execute(stmt)
        reviews = res.scalars().all()
        return [
            BookReviewDTO(
                id=r.id,
                bookId=r.book_id,
                author=r.author_name,
                avatar=r.avatar_url,
                rating=r.rating or 5.0,
                time=r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "اخیراً",
                content=r.content,
                isApproved=r.is_approved,
                status="approved" if r.is_approved else "pending"
            ) for r in reviews
        ]

    @staticmethod
    async def create_book_review(
        db: AsyncSession,
        book_id: str,
        user_id: Optional[str],
        author_name: str,
        rating: float,
        content: str,
        avatar_url: Optional[str] = None
    ) -> BookReviewDTO:
        book = await db.get(Book, book_id)
        if not book:
            raise BookNotFoundException()

        review_id = f"rev_{uuid.uuid4().hex[:12]}"
        review = BookReview(
            id=review_id,
            book_id=book_id,
            user_id=user_id,
            author_name=author_name or "کاربر گرامی سامانه اتحاد",
            avatar_url=avatar_url,
            rating=float(rating),
            content=content.strip(),
            is_approved=True
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)
        return BookReviewDTO(
            id=review.id,
            bookId=review.book_id,
            author=review.author_name,
            avatar=review.avatar_url,
            rating=review.rating,
            time="هم‌اکنون",
            content=review.content,
            isApproved=review.is_approved,
            status="approved"
        )




