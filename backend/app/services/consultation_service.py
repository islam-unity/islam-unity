import uuid
import random
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.orm import selectinload

from app.db.base import utc_now
from app.db.models import (
    Scholar, ConsultationThread, ConsultationMessage,
    ConsultationAttachment, ScholarQuickReply, User
)
from app.schemas.consultation import (
    CreateThreadRequest, CreateMessageRequest, CreateQuickReplyRequest,
    ScholarDTO, ThreadListItemDTO, ThreadDetailDTO, ConsultationMessageDTO,
    AttachmentDTO, BookReferenceDTO, ScholarCitationSuggestionItem
)
from app.core.exceptions import (
    ThreadNotFoundException, AccessDeniedException, AppException
)
from app.core.websocket_manager import ws_manager


class ConsultationService:
    @staticmethod
    async def get_scholars(
        db: AsyncSession,
        q: Optional[str] = None,
        madhhab: Optional[str] = None,
        city: Optional[str] = None,
        mosque: Optional[str] = None,
        specialty: Optional[str] = None,
        min_rating: Optional[float] = None,
        sort: Optional[str] = "RANK_RATING",
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        stmt = select(Scholar)

        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(or_(
                Scholar.name.ilike(pattern),
                Scholar.title.ilike(pattern),
                Scholar.bio.ilike(pattern)
            ))
        if madhhab:
            stmt = stmt.where(Scholar.madhhab == madhhab)
        if city:
            stmt = stmt.where(Scholar.city == city)
        if mosque:
            stmt = stmt.where(Scholar.mosque.ilike(f"%{mosque}%"))
        if min_rating:
            stmt = stmt.where(Scholar.rating >= min_rating)

        # Sorting
        if sort == "ANSWERS_COUNT":
            stmt = stmt.order_by(desc(Scholar.answer_count))
        elif sort == "RESPONSE_SPEED":
            stmt = stmt.order_by(asc(Scholar.response_time_hours))
        else:  # RANK_RATING default
            stmt = stmt.order_by(asc(Scholar.rank), desc(Scholar.rating))

        # Total count query
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await db.scalar(count_stmt) or 0

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await db.execute(stmt)
        scholars = result.scalars().all()

        scholar_dtos = []
        for s in scholars:
            # In-memory specialty filter if specified
            if specialty and specialty not in (s.specialties or []):
                continue
            scholar_dtos.append(ScholarDTO(
                id=s.id,
                name=s.name,
                title=s.title,
                specialties=s.specialties or [],
                rating=s.rating,
                answerCount=s.answer_count,
                responseTimeHours=s.response_time_hours,
                rank=s.rank,
                avatarColorHex=s.avatar_color_hex,
                avatarUrl=s.avatar_url,
                isVerified=s.is_verified,
                madhhab=s.madhhab,
                city=s.city,
                mosque=s.mosque,
                bio=s.bio
            ))

        return {
            "items": scholar_dtos,
            "meta": {
                "page": page,
                "limit": limit,
                "totalCount": total_count,
                "hasMore": (offset + len(scholar_dtos)) < total_count
            }
        }

    @staticmethod
    async def get_scholars_metadata(db: AsyncSession) -> Dict[str, List[str]]:
        scholars_res = await db.execute(select(Scholar))
        scholars = scholars_res.scalars().all()

        cities = sorted(list(set(s.city for s in scholars if s.city)))
        mosques = sorted(list(set(s.mosque for s in scholars if s.mosque)))
        madhhabs = sorted(list(set(s.madhhab for s in scholars if s.madhhab)))
        specialties_set = set()
        for s in scholars:
            for sp in (s.specialties or []):
                specialties_set.add(sp)

        return {
            "cities": cities,
            "mosques": mosques,
            "madhhabs": madhhabs,
            "specialties": sorted(list(specialties_set))
        }

    @staticmethod
    async def create_thread(
        db: AsyncSession,
        user_id: str,
        data: CreateThreadRequest
    ) -> Dict[str, Any]:
        # Enforce max 5 concurrent active scholar consultations per user
        active_count_stmt = select(func.count(ConsultationThread.id)).where(
            ConsultationThread.user_id == user_id,
            ConsultationThread.status.in_(["WAITING_SCHOLAR", "OPEN"])
        )
        active_count = await db.scalar(active_count_stmt) or 0
        if active_count >= 5:
            raise AppException(
                code="SCHOLAR_LIMIT_REACHED",
                message="سقف مجاز گفتگوی همزمان تکمیل است. حداکثر ۵ گفتگوی همزمان با علما مجاز می‌باشد. لطفاً جهت آغاز مشاوره جدید، یکی از گفتگوهای قبلی را پایان دهید.",
                status_code=400
            )

        thread_id = f"thread_{random.randint(100000, 999999)}"
        tracking_code = f"ETH-Q-{random.randint(10000, 99999)}"

        thread = ConsultationThread(
            id=thread_id,
            user_id=user_id,
            target_scholar_id=data.targetScholarId,
            title=data.title,
            category=data.category,
            tracking_code=tracking_code,
            status="WAITING_SCHOLAR",
            is_anonymous=data.isAnonymous,
            is_public=data.isPublic,
            is_urgent=data.isUrgent,
            is_bookmarked=False
        )
        db.add(thread)

        # Initial question message
        init_message = ConsultationMessage(
            id=f"msg_{uuid.uuid4().hex[:10]}",
            thread_id=thread_id,
            sender_id=user_id,
            sender_role="SEEKER",
            text=data.initialQuestionBody,
            is_read=True
        )
        db.add(init_message)

        # Add attachments if provided
        if data.attachments:
            for att in data.attachments:
                attachment_obj = ConsultationAttachment(
                    id=att.mediaId,
                    thread_id=thread_id,
                    uploader_id=user_id,
                    type=att.type,
                    title=att.title,
                    duration_seconds=att.durationSeconds,
                    file_url=att.fileUrl,
                    file_size_bytes=att.fileSizeBytes
                )
                db.add(attachment_obj)

        await db.commit()

        return {
            "threadId": thread_id,
            "status": "WAITING_SCHOLAR",
            "createdAtFa": "امروز - هم‌اکنون",
            "trackingCode": tracking_code
        }

    @staticmethod
    async def get_threads(
        db: AsyncSession,
        user_id: str,
        role: str,
        filter_type: str = "ALL",
        category: Optional[str] = None,
        q: Optional[str] = None,
        sort: str = "LAST_ACTIVITY",
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        stmt = select(ConsultationThread).options(
            selectinload(ConsultationThread.target_scholar),
            selectinload(ConsultationThread.messages)
        )

        if filter_type == "PUBLIC":
            stmt = stmt.where(ConsultationThread.is_public == True)
        elif role == "SEEKER":
            stmt = stmt.where(ConsultationThread.user_id == user_id)
            if filter_type == "PENDING":
                stmt = stmt.where(ConsultationThread.status == "WAITING_SCHOLAR")
            elif filter_type == "ANSWERED":
                stmt = stmt.where(ConsultationThread.status == "ANSWERED")
            elif filter_type == "BOOKMARKED":
                stmt = stmt.where(ConsultationThread.is_bookmarked == True)

        if category:
            stmt = stmt.where(ConsultationThread.category == category)
        if q:
            stmt = stmt.where(ConsultationThread.title.ilike(f"%{q}%"))

        if sort == "NEWEST":
            stmt = stmt.order_by(desc(ConsultationThread.created_at))
        else:
            stmt = stmt.order_by(desc(ConsultationThread.updated_at))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = await db.scalar(count_stmt) or 0

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        threads_res = await db.execute(stmt)
        threads = threads_res.scalars().all()

        items = []
        for t in threads:
            last_msg = t.messages[-1].text if t.messages else None
            scholar_name = t.target_scholar.name if t.target_scholar else "منتظر انتساب عالم"
            items.append(ThreadListItemDTO(
                id=t.id,
                title=t.title,
                category=t.category,
                status=t.status,
                trackingCode=t.tracking_code,
                isUrgent=t.is_urgent,
                isBookmarked=t.is_bookmarked,
                isPublic=t.is_public,
                lastMessage=last_msg,
                createdAtFa="امروز",
                scholarName=scholar_name
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
    async def get_thread_detail(
        db: AsyncSession,
        thread_id: str,
        user_id: str,
        role: str
    ) -> ThreadDetailDTO:
        stmt = select(ConsultationThread).options(
            selectinload(ConsultationThread.target_scholar),
            selectinload(ConsultationThread.messages).selectinload(ConsultationMessage.attachment),
            selectinload(ConsultationThread.attachments)
        ).where(ConsultationThread.id == thread_id)

        thread = await db.scalar(stmt)
        if not thread:
            raise ThreadNotFoundException()

        # Check access permission if private
        if not thread.is_public and thread.user_id != user_id and role != "SCHOLAR":
            raise AccessDeniedException()

        scholar_dto = None
        if thread.target_scholar:
            s = thread.target_scholar
            scholar_dto = ScholarDTO(
                id=s.id,
                name=s.name,
                title=s.title,
                specialties=s.specialties or [],
                rating=s.rating,
                answerCount=s.answer_count,
                responseTimeHours=s.response_time_hours,
                rank=s.rank,
                avatarColorHex=s.avatar_color_hex,
                avatarUrl=s.avatar_url,
                isVerified=s.is_verified,
                madhhab=s.madhhab,
                city=s.city,
                mosque=s.mosque,
                bio=s.bio
            )

        msg_dtos = []
        for m in thread.messages:
            att_dto = None
            if m.attachment:
                att_dto = AttachmentDTO(
                    mediaId=m.attachment.id,
                    type=m.attachment.type,
                    title=m.attachment.title,
                    durationSeconds=m.attachment.duration_seconds,
                    fileUrl=m.attachment.file_url,
                    fileSizeBytes=m.attachment.file_size_bytes
                )
            book_ref_dto = BookReferenceDTO(**m.book_reference) if m.book_reference else None
            msg_dtos.append(ConsultationMessageDTO(
                id=m.id,
                threadId=m.thread_id,
                senderId=m.sender_id,
                senderRole=m.sender_role,
                text=m.text,
                citation=m.citation,
                bookReference=book_ref_dto,
                attachment=att_dto,
                isRead=m.is_read,
                createdAt=m.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            ))

        att_dtos = [
            AttachmentDTO(
                mediaId=a.id,
                type=a.type,
                title=a.title,
                durationSeconds=a.duration_seconds,
                fileUrl=a.file_url,
                fileSizeBytes=a.file_size_bytes
            ) for a in thread.attachments
        ]

        return ThreadDetailDTO(
            id=thread.id,
            title=thread.title,
            category=thread.category,
            status=thread.status,
            trackingCode=thread.tracking_code,
            isAnonymous=thread.is_anonymous,
            isPublic=thread.is_public,
            isUrgent=thread.is_urgent,
            isBookmarked=thread.is_bookmarked,
            createdAt=thread.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            scholar=scholar_dto,
            messages=msg_dtos,
            attachments=att_dtos
        )

    @staticmethod
    async def send_message(
        db: AsyncSession,
        thread_id: str,
        user_id: str,
        role: str,
        data: CreateMessageRequest
    ) -> ConsultationMessageDTO:
        thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == thread_id))
        if not thread:
            raise ThreadNotFoundException()

        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        book_ref_dict = data.bookReference.model_dump() if data.bookReference else None
        msg = ConsultationMessage(
            id=msg_id,
            thread_id=thread_id,
            sender_id=user_id,
            sender_role=role,
            text=data.text,
            citation=data.citation,
            book_reference=book_ref_dict,
            attachment_id=data.attachmentId,
            is_read=False
        )
        db.add(msg)

        # Update thread state
        if role == "SCHOLAR":
            thread.status = "ANSWERED"
        thread.updated_at = utc_now()

        await db.commit()
        await db.refresh(msg)

        book_ref_dto = BookReferenceDTO(**msg.book_reference) if msg.book_reference else None
        msg_dto = ConsultationMessageDTO(
            id=msg.id,
            threadId=msg.thread_id,
            senderId=msg.sender_id,
            senderRole=msg.sender_role,
            text=msg.text,
            citation=msg.citation,
            bookReference=book_ref_dto,
            attachment=None,
            isRead=msg.is_read,
            createdAt=msg.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        )

        # Broadcast via WebSocket channel
        await ws_manager.broadcast_to_channel(
            channel=f"consultation:{thread_id}",
            event_type="NEW_MESSAGE",
            payload=msg_dto.model_dump()
        )

        return msg_dto

    @staticmethod
    async def search_books_for_citation(
        db: AsyncSession,
        query: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Allows scholars to search books, chapters, and topics in the library
        to cite or send a passage or entire book to seekers in consultation chat.
        """
        from app.db.models import Book, BookChapter
        stmt = select(Book).options(selectinload(Book.category), selectinload(Book.chapters))
        if query:
            pat = f"%{query}%"
            stmt = stmt.where(or_(
                Book.title.ilike(pat),
                Book.author.ilike(pat),
                Book.description.ilike(pat)
            ))
        stmt = stmt.limit(limit)
        res = await db.execute(stmt)
        books = res.scalars().all()

        results = []
        for b in books:
            ch_list = []
            for c in b.chapters:
                sample_quote = (c.paragraphs[0] if c.paragraphs else (c.content[:160] + "...")) if c.content else ""
                ch_list.append({
                    "chapterId": c.id,
                    "chapterNumber": c.chapter_number,
                    "title": c.title,
                    "sampleQuote": sample_quote
                })
            results.append({
                "bookId": b.id,
                "title": b.title,
                "author": b.author,
                "coverUrl": b.cover_url,
                "categoryTitle": b.category.title if b.category else "عمومی",
                "topics": b.topics or [],
                "chapters": ch_list
            })
        return results

    @staticmethod
    async def suggest_citations_for_thread(
        db: AsyncSession,
        thread_id: str,
        scholar_id: str
    ) -> List[ScholarCitationSuggestionItem]:
        """
        AI-assisted citation recommender for scholars:
        Analyzes the seeker's thread question and dialogue history, searches library RAG/SQL,
        and provides 2-3 ready-to-cite passages with quote, page, chapter, and book deep links.
        """
        thread = await db.scalar(
            select(ConsultationThread).options(
                selectinload(ConsultationThread.messages)
            ).where(ConsultationThread.id == thread_id)
        )
        if not thread:
            raise ThreadNotFoundException()

        last_msgs = [m.text for m in (thread.messages or [])][-3:]
        inquiry_text = f"{thread.title} {thread.category} {' '.join(last_msgs)}".strip()

        from app.services.library_service import LibraryService
        search_results = await LibraryService.semantic_search(db=db, query=inquiry_text, limit=3)

        suggestions = []
        for sr in search_results:
            suggestions.append(ScholarCitationSuggestionItem(
                bookId=sr.bookId,
                bookTitle=sr.bookTitle,
                author=sr.author or "مؤلف اسلامی",
                coverUrl=sr.coverUrl,
                chapterId=sr.chapterId,
                chapterTitle=sr.chapterTitle,
                pageNumber=1,
                paragraphIndex=0,
                quote=sr.excerpt,
                relevanceReason=f"این فراز از کتاب «{sr.bookTitle}» مستقیماً به موضوع «{thread.category}» و پرسش مطرح‌شده در این گفتگو پاسخ می‌دهد.",
                confidenceScore=sr.relevanceScore,
                type="PASSAGE_CITATION"
            ))

        return suggestions

    @staticmethod
    async def update_thread_status(db: AsyncSession, thread_id: str, user_id: str, status: str):
        thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == thread_id))
        if not thread:
            raise ThreadNotFoundException()
        thread.status = status
        await db.commit()
        return {"threadId": thread_id, "status": thread.status}

    @staticmethod
    async def toggle_bookmark(db: AsyncSession, thread_id: str, user_id: str):
        thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == thread_id))
        if not thread:
            raise ThreadNotFoundException()
        thread.is_bookmarked = not thread.is_bookmarked
        await db.commit()
        return {"threadId": thread_id, "isBookmarked": thread.is_bookmarked}

    @staticmethod
    async def update_visibility(db: AsyncSession, thread_id: str, user_id: str, is_public: bool):
        thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == thread_id))
        if not thread:
            raise ThreadNotFoundException()
        thread.is_public = is_public
        await db.commit()
        return {"threadId": thread_id, "isPublic": thread.is_public}

    @staticmethod
    async def get_scholar_inbox(db: AsyncSession, scholar_id: Optional[str] = None) -> List[ThreadListItemDTO]:
        stmt = select(ConsultationThread).where(
            ConsultationThread.status.in_(["WAITING_SCHOLAR", "OPEN"])
        ).order_by(desc(ConsultationThread.is_urgent), desc(ConsultationThread.created_at))

        res = await db.execute(stmt)
        threads = res.scalars().all()
        return [
            ThreadListItemDTO(
                id=t.id,
                title=t.title,
                category=t.category,
                status=t.status,
                trackingCode=t.tracking_code,
                isUrgent=t.is_urgent,
                isBookmarked=t.is_bookmarked,
                isPublic=t.is_public,
                createdAtFa="امروز",
                scholarName="ارجاع‌شده به شما"
            ) for t in threads
        ]

    @staticmethod
    async def get_quick_replies(db: AsyncSession, scholar_id: Optional[str] = None):
        stmt = select(ScholarQuickReply)
        if scholar_id:
            stmt = stmt.where(or_(ScholarQuickReply.scholar_id == scholar_id, ScholarQuickReply.scholar_id.is_(None)))
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def create_quick_reply(db: AsyncSession, scholar_id: str, data: CreateQuickReplyRequest):
        qr_id = f"qr_{uuid.uuid4().hex[:8]}"
        qr = ScholarQuickReply(
            id=qr_id,
            scholar_id=scholar_id,
            title=data.title,
            content=data.content,
            category=data.category or "عمومی"
        )
        db.add(qr)
        await db.commit()
        await db.refresh(qr)
        return qr

    @staticmethod
    async def generate_ai_draft_response(
        db: AsyncSession,
        thread_id: str,
        scholar_id: str
    ) -> Dict[str, Any]:
        """
        Assists scholars by generating a suggested scholarly draft response for a consultation thread
        using the dedicated 'consultation' section model & base URL.
        """
        thread = await db.scalar(select(ConsultationThread).where(ConsultationThread.id == thread_id))
        if not thread:
            raise ThreadNotFoundException()

        first_msg = await db.scalar(
            select(ConsultationMessage)
            .where(ConsultationMessage.thread_id == thread_id)
            .order_by(ConsultationMessage.created_at)
        )
        question_text = first_msg.text if first_msg else thread.title

        from app.services.llm_provider_service import LLMProviderService
        sys_prompt = (
            "شما دستیار فقهی و مشاوره‌ای سامانه اتحاد برای اساتید و علمای دینی هستید. "
            "بر اساس استفتای مطرح‌شده، یک پیش‌نویس پاسخ مستدل، متقن، مؤدبانه و فقهی پیشنهاد دهید."
        )
        llm_res = await LLMProviderService.call_chat_generation(
            section_key="consultation",
            system_prompt=sys_prompt,
            user_query=f"موضوع: {thread.title}\nدسته‌بندی: {thread.category}\nمتن سوال: {question_text}",
            db=db
        )
        draft_text = llm_res.get("text") if llm_res and llm_res.get("text") else (
            f"سلام علیکم و رحمة الله.\nدر پاسخ به پرسش مطروحه درباره «{thread.title}»، بر اساس مبانی فقهی و موازین شرعی، چنانچه شرایط و قیود شرعی رعایت گردد، عمل مجاز است؛ لکن در جزئیات توصیه می‌شود به فتوای مرجع تقلید خویش یا توضیحات تفصیلی ذیل رجوع فرمایید."
        )
        return {
            "threadId": thread_id,
            "suggestedDraft": draft_text,
            "modelUsed": llm_res.get("model_used") if llm_res else "consultation-model",
            "category": thread.category
        }
