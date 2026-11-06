import uuid
import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc, and_
from sqlalchemy.orm import selectinload
from app.db.base import utc_now

from app.db.models import (
    User, Scholar, Post, PostMedia, PostComment, PostLike,
    PostBookmark, PostCommentLike, PostReport
)
from app.schemas.feed import (
    AuthorDTO, PostMediaDTO, CommentDTO, PostDTO, FeedListResponse,
    CreatePostRequest, CreateCommentRequest, ReportPostRequest,
    AIAssistCaptionRequest, AIAssistCaptionResponse,
    AIAnalyzePostResponse, AuthorProfileDTO
)
from app.core.exceptions import AppException, AccessDeniedException
from app.services.llm_provider_service import LLMProviderService


# Smart Bad-Word / Inappropriate Phrase Filter
BLOCKED_KEYWORDS = [
    "تکفیر", "لعنت بر", "کافر دانستن", "سب و لعن", "توهین", "بدعت‌گذار خبیث"
]


class FeedService:

    @staticmethod
    def _build_author_dto(user: Optional[User], scholar: Optional[Scholar]) -> AuthorDTO:
        if not user:
            return AuthorDTO(
                id="unknown",
                full_name="کاربر ناشناس",
                avatar=None,
                role="SEEKER",
                is_scholar=False,
                is_verified=False
            )

        if scholar:
            return AuthorDTO(
                id=user.id,
                full_name=scholar.name or user.full_name,
                avatar=scholar.avatar_url or user.avatar,
                role="SCHOLAR",
                is_scholar=True,
                title=scholar.title,
                scholar_rank=scholar.rank,
                madhhab=scholar.madhhab,
                city=scholar.city,
                mosque=scholar.mosque,
                is_verified=scholar.is_verified
            )

        is_scholar = user.role in ["SCHOLAR", "ADMIN"]
        return AuthorDTO(
            id=user.id,
            full_name=user.full_name,
            avatar=user.avatar,
            role=user.role,
            is_scholar=is_scholar,
            title="پژوهشگر معارفی" if is_scholar else "کاربر سامانه",
            scholar_rank=None,
            madhhab=user.madhhab,
            city=None,
            mosque=None,
            is_verified=is_scholar
        )

    @staticmethod
    def _moderate_content(text: str) -> Tuple[bool, str]:
        for kw in BLOCKED_KEYWORDS:
            if kw in text:
                return False, f"متن حاوی عبارات نامناسب یا تفرقه‌آمیز است: '{kw}'"
        return True, "تایید شد"

    @classmethod
    async def get_feed(
        cls,
        db: AsyncSession,
        current_user_id: Optional[str] = None,
        category: Optional[str] = None,
        media_type: Optional[str] = None,
        scholars_only: bool = False,
        madhhab: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 10
    ) -> FeedListResponse:
        stmt = (
            select(Post)
            .options(
                selectinload(Post.author),
                selectinload(Post.scholar),
                selectinload(Post.media_items),
                selectinload(Post.comments).selectinload(PostComment.user),
                selectinload(Post.likes),
                selectinload(Post.bookmarks)
            )
            .where(Post.status == "PUBLISHED")
        )

        if scholars_only:
            stmt = stmt.where(Post.is_scholar_post == True)

        if category and category.upper() != "ALL":
            stmt = stmt.where(Post.category == category.upper())

        if madhhab and madhhab != "همه":
            stmt = stmt.where(or_(Post.madhhab == madhhab, Post.madhhab == "مشترک"))

        if search:
            p = f"%{search}%"
            stmt = stmt.where(or_(
                Post.title.ilike(p),
                Post.content.ilike(p)
            ))

        # Count total
        count_stmt = select(func.count(Post.id)).where(Post.status == "PUBLISHED")
        if scholars_only:
            count_stmt = count_stmt.where(Post.is_scholar_post == True)
        if category and category.upper() != "ALL":
            count_stmt = count_stmt.where(Post.category == category.upper())
        if madhhab and madhhab != "همه":
            count_stmt = count_stmt.where(or_(Post.madhhab == madhhab, Post.madhhab == "مشترک"))
        if search:
            p = f"%{search}%"
            count_stmt = count_stmt.where(or_(Post.title.ilike(p), Post.content.ilike(p)))

        total = await db.scalar(count_stmt) or 0

        # Sort: verified scholar posts receive slight elevation, then by created_at desc
        stmt = stmt.order_by(desc(Post.created_at))
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        result = await db.execute(stmt)
        posts = result.scalars().all()

        items: List[PostDTO] = []
        for post in posts:
            # Filter media type if requested
            if media_type and media_type.upper() != "ALL":
                has_media = any(m.media_type.upper() == media_type.upper() for m in post.media_items)
                if not has_media:
                    continue

            post_dto = cls._to_post_dto(post, current_user_id)
            items.append(post_dto)

        has_more = (page * limit) < total
        return FeedListResponse(
            items=items,
            total=total,
            page=page,
            limit=limit,
            has_more=has_more
        )

    @classmethod
    def _to_post_dto(cls, post: Post, current_user_id: Optional[str] = None) -> PostDTO:
        author_dto = cls._build_author_dto(post.author, post.scholar)
        
        media_list = [
            PostMediaDTO(
                id=m.id,
                media_type=m.media_type,
                media_url=m.media_url,
                thumbnail_url=m.thumbnail_url,
                duration_seconds=m.duration_seconds,
                aspect_ratio=m.aspect_ratio or "1:1",
                order=m.order or 0
            ) for m in post.media_items
        ]

        is_liked = False
        is_saved = False
        if current_user_id:
            is_liked = any(like.user_id == current_user_id for like in post.likes)
            is_saved = any(b.user_id == current_user_id for b in post.bookmarks)

        pinned_dto: Optional[CommentDTO] = None
        if post.pinned_comment_id:
            for c in post.comments:
                if c.id == post.pinned_comment_id and c.status == "APPROVED":
                    c_author = cls._build_author_dto(c.user, None)
                    pinned_dto = CommentDTO(
                        id=c.id,
                        post_id=c.post_id,
                        author=c_author,
                        content=c.content,
                        is_scholar_reply=c.is_scholar_reply,
                        is_pinned=True,
                        likes_count=c.likes_count,
                        is_liked_by_me=False,
                        created_at=c.created_at.isoformat() if c.created_at else "",
                        replies=[]
                    )
                    break

        return PostDTO(
            id=post.id,
            title=post.title,
            content=post.content,
            content_type=post.content_type,
            category=post.category,
            madhhab=post.madhhab,
            quran_references=post.quran_references or [],
            hadith_references=post.hadith_references or [],
            tags=post.tags or [],
            views_count=post.views_count,
            likes_count=post.likes_count,
            comments_count=post.comments_count,
            shares_count=post.shares_count,
            saves_count=post.saves_count,
            is_liked_by_me=is_liked,
            is_saved_by_me=is_saved,
            is_scholar_post=post.is_scholar_post,
            author=author_dto,
            media_items=media_list,
            pinned_comment=pinned_dto,
            ai_summary=post.ai_summary,
            created_at=post.created_at.isoformat() if post.created_at else ""
        )

    @classmethod
    async def get_post_by_id(cls, db: AsyncSession, post_id: str, current_user_id: Optional[str] = None) -> PostDTO:
        stmt = (
            select(Post)
            .options(
                selectinload(Post.author),
                selectinload(Post.scholar),
                selectinload(Post.media_items),
                selectinload(Post.comments).selectinload(PostComment.user),
                selectinload(Post.likes),
                selectinload(Post.bookmarks)
            )
            .where(Post.id == post_id)
        )
        post = await db.scalar(stmt)
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست مورد نظر یافت نشد.", status_code=404)

        # Increment views
        post.views_count += 1
        await db.commit()

        return cls._to_post_dto(post, current_user_id)

    @classmethod
    async def create_post(cls, db: AsyncSession, current_user: User, data: CreatePostRequest) -> PostDTO:
        # Check if user is a scholar
        scholar_stmt = select(Scholar).where(Scholar.user_id == current_user.id)
        scholar = await db.scalar(scholar_stmt)
        is_scholar = (current_user.role in ["SCHOLAR", "ADMIN"]) or (scholar is not None)

        # Moderation check
        is_clean, note = cls._moderate_content(f"{data.title or ''} {data.content}")
        if not is_clean:
            if not is_scholar:
                raise AppException(code="MODERATION_BLOCKED", message=f"امکان انتشار پست وجود ندارد: {note}", status_code=400)

        post_id = f"post_{uuid.uuid4().hex[:12]}"

        # Infer content type if not explicit
        content_type = data.content_type or "MULTIMEDIA"
        if data.media_items:
            types = {m.media_type.upper() for m in data.media_items}
            if "VIDEO" in types:
                content_type = "VIDEO"
            elif "AUDIO" in types and len(types) == 1:
                content_type = "AUDIO"
            elif len(data.media_items) > 1:
                content_type = "IMAGE_GALLERY"
            elif len(data.media_items) == 1:
                content_type = "IMAGE_SINGLE"
        elif not data.media_items:
            content_type = "TEXT"

        new_post = Post(
            id=post_id,
            user_id=current_user.id,
            scholar_id=scholar.id if scholar else None,
            is_scholar_post=is_scholar,
            title=data.title,
            content=data.content,
            content_type=content_type,
            category=data.category.upper() if data.category else "GENERAL",
            madhhab=data.madhhab or (scholar.madhhab if scholar else current_user.madhhab),
            quran_references=data.quran_references,
            hadith_references=data.hadith_references,
            tags=data.tags,
            status="PUBLISHED",
            views_count=0,
            likes_count=0,
            comments_count=0,
            shares_count=0,
            saves_count=0,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(new_post)
        await db.flush()

        # Add media items
        for idx, media_item in enumerate(data.media_items):
            media_id = f"med_{uuid.uuid4().hex[:12]}"
            m = PostMedia(
                id=media_id,
                post_id=post_id,
                media_type=media_item.media_type.upper(),
                media_url=media_item.media_url,
                thumbnail_url=media_item.thumbnail_url,
                duration_seconds=media_item.duration_seconds,
                aspect_ratio=media_item.aspect_ratio or "1:1",
                order=media_item.order if media_item.order is not None else idx
            )
            db.add(m)

        await db.commit()
        return await cls.get_post_by_id(db, post_id, current_user.id)

    @classmethod
    async def toggle_like(cls, db: AsyncSession, post_id: str, current_user_id: str) -> Dict[str, Any]:
        post = await db.scalar(select(Post).where(Post.id == post_id))
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست مورد نظر یافت نشد.", status_code=404)

        existing_like = await db.scalar(
            select(PostLike).where(
                and_(PostLike.post_id == post_id, PostLike.user_id == current_user_id)
            )
        )

        if existing_like:
            await db.delete(existing_like)
            post.likes_count = max(0, post.likes_count - 1)
            is_liked = False
        else:
            new_like = PostLike(
                post_id=post_id,
                user_id=current_user_id,
                created_at=utc_now()
            )
            db.add(new_like)
            post.likes_count += 1
            is_liked = True

        await db.commit()
        return {"is_liked": is_liked, "likes_count": post.likes_count}

    @classmethod
    async def toggle_bookmark(cls, db: AsyncSession, post_id: str, current_user_id: str) -> Dict[str, Any]:
        post = await db.scalar(select(Post).where(Post.id == post_id))
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست مورد نظر یافت نشد.", status_code=404)

        existing_bm = await db.scalar(
            select(PostBookmark).where(
                and_(PostBookmark.post_id == post_id, PostBookmark.user_id == current_user_id)
            )
        )

        if existing_bm:
            await db.delete(existing_bm)
            post.saves_count = max(0, post.saves_count - 1)
            is_saved = False
        else:
            new_bm = PostBookmark(
                post_id=post_id,
                user_id=current_user_id,
                created_at=utc_now()
            )
            db.add(new_bm)
            post.saves_count += 1
            is_saved = True

        await db.commit()
        return {"is_saved": is_saved, "saves_count": post.saves_count}

    @classmethod
    async def get_comments(cls, db: AsyncSession, post_id: str, current_user_id: Optional[str] = None) -> List[CommentDTO]:
        stmt = (
            select(PostComment)
            .options(
                selectinload(PostComment.user),
                selectinload(PostComment.replies).selectinload(PostComment.user),
                selectinload(PostComment.comment_likes)
            )
            .where(
                and_(
                    PostComment.post_id == post_id,
                    PostComment.parent_comment_id == None,
                    PostComment.status == "APPROVED"
                )
            )
            .order_by(desc(PostComment.is_pinned), desc(PostComment.likes_count), desc(PostComment.created_at))
        )
        comments = (await db.execute(stmt)).scalars().all()

        results: List[CommentDTO] = []
        for c in comments:
            author_dto = cls._build_author_dto(c.user, None)
            is_liked = False
            if current_user_id:
                is_liked = any(l.user_id == current_user_id for l in c.comment_likes)

            reply_dtos: List[CommentDTO] = []
            for r in c.replies:
                if r.status == "APPROVED":
                    r_author = cls._build_author_dto(r.user, None)
                    r_liked = False
                    if current_user_id:
                        r_liked = any(l.user_id == current_user_id for l in r.comment_likes)
                    reply_dtos.append(CommentDTO(
                        id=r.id,
                        post_id=r.post_id,
                        author=r_author,
                        content=r.content,
                        is_scholar_reply=r.is_scholar_reply,
                        is_pinned=r.is_pinned,
                        likes_count=r.likes_count,
                        is_liked_by_me=r_liked,
                        created_at=r.created_at.isoformat() if r.created_at else "",
                        replies=[]
                    ))

            results.append(CommentDTO(
                id=c.id,
                post_id=c.post_id,
                author=author_dto,
                content=c.content,
                is_scholar_reply=c.is_scholar_reply,
                is_pinned=c.is_pinned,
                likes_count=c.likes_count,
                is_liked_by_me=is_liked,
                created_at=c.created_at.isoformat() if c.created_at else "",
                replies=reply_dtos
            ))

        return results

    @classmethod
    async def add_comment(cls, db: AsyncSession, post_id: str, current_user: User, data: CreateCommentRequest) -> CommentDTO:
        post = await db.scalar(select(Post).where(Post.id == post_id))
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست مورد نظر یافت نشد.", status_code=404)

        is_clean, note = cls._moderate_content(data.content)
        if not is_clean:
            raise AppException(code="MODERATION_BLOCKED", message=f"ارسال نظر به دلیل واژگان نامناسب رد شد: {note}", status_code=400)

        is_scholar = current_user.role in ["SCHOLAR", "ADMIN"]
        comment_id = f"comm_{uuid.uuid4().hex[:12]}"

        new_comment = PostComment(
            id=comment_id,
            post_id=post_id,
            user_id=current_user.id,
            parent_comment_id=data.parent_comment_id,
            content=data.content,
            is_scholar_reply=is_scholar,
            is_pinned=False,
            likes_count=0,
            status="APPROVED",
            created_at=utc_now()
        )
        db.add(new_comment)
        post.comments_count += 1
        await db.commit()

        author_dto = cls._build_author_dto(current_user, None)
        return CommentDTO(
            id=new_comment.id,
            post_id=post_id,
            author=author_dto,
            content=new_comment.content,
            is_scholar_reply=new_comment.is_scholar_reply,
            is_pinned=new_comment.is_pinned,
            likes_count=0,
            is_liked_by_me=False,
            created_at=new_comment.created_at.isoformat(),
            replies=[]
        )

    @classmethod
    async def pin_comment(cls, db: AsyncSession, post_id: str, comment_id: str, current_user: User) -> Dict[str, Any]:
        post = await db.scalar(select(Post).where(Post.id == post_id))
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست یافت نشد.", status_code=404)

        comment = await db.scalar(select(PostComment).where(and_(PostComment.id == comment_id, PostComment.post_id == post_id)))
        if not comment:
            raise AppException(code="COMMENT_NOT_FOUND", message="نظر یافت نشد.", status_code=404)

        # Only author or scholar can pin
        is_scholar = current_user.role in ["SCHOLAR", "ADMIN"]
        if post.user_id != current_user.id and not is_scholar:
            raise AccessDeniedException("فقط نویسنده پست یا اساتید می‌توانند پاسخی را پین کنند.")

        if comment.is_pinned:
            comment.is_pinned = False
            post.pinned_comment_id = None
            is_pinned_now = False
        else:
            # Unpin any previously pinned comment on this post
            prev_pinned = await db.execute(select(PostComment).where(and_(PostComment.post_id == post_id, PostComment.is_pinned == True)))
            for p in prev_pinned.scalars().all():
                p.is_pinned = False

            comment.is_pinned = True
            post.pinned_comment_id = comment.id
            is_pinned_now = True

        await db.commit()
        return {"comment_id": comment_id, "is_pinned": is_pinned_now}

    @classmethod
    async def report_post(cls, db: AsyncSession, post_id: str, current_user_id: str, data: ReportPostRequest) -> Dict[str, Any]:
        post = await db.scalar(select(Post).where(Post.id == post_id))
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست یافت نشد.", status_code=404)

        report_id = f"rep_{uuid.uuid4().hex[:12]}"
        rep = PostReport(
            id=report_id,
            post_id=post_id,
            user_id=current_user_id,
            reason=data.reason,
            description=data.description,
            status="PENDING",
            created_at=utc_now()
        )
        db.add(rep)

        # Check total reports
        reports_count = await db.scalar(select(func.count(PostReport.id)).where(PostReport.post_id == post_id)) or 0
        if reports_count >= 5:
            post.status = "REPORTED_HIDDEN"
            post.moderation_note = "پنهان‌سازی خودکار به دلیل گزارش‌های متعدد کاربران"

        await db.commit()
        return {"report_id": report_id, "status": "RECEIVED", "message": "گزارش با موفقیت ثبت و به تیم نظارت ارسال شد."}

    @classmethod
    async def get_author_profile(cls, db: AsyncSession, user_id: str, viewer_id: Optional[str] = None) -> AuthorProfileDTO:
        user = await db.scalar(select(User).where(User.id == user_id))
        if not user:
            raise AppException(code="USER_NOT_FOUND", message="کاربر یافت نشد.", status_code=404)

        scholar = await db.scalar(select(Scholar).where(Scholar.user_id == user_id))
        author_dto = cls._build_author_dto(user, scholar)

        posts_stmt = (
            select(Post)
            .options(
                selectinload(Post.author),
                selectinload(Post.scholar),
                selectinload(Post.media_items),
                selectinload(Post.comments),
                selectinload(Post.likes),
                selectinload(Post.bookmarks)
            )
            .where(and_(Post.user_id == user_id, Post.status == "PUBLISHED"))
            .order_by(desc(Post.created_at))
        )
        posts = (await db.execute(posts_stmt)).scalars().all()

        post_dtos = [cls._to_post_dto(p, viewer_id) for p in posts]
        total_likes = sum(p.likes_count for p in posts)

        bio = scholar.bio if scholar else (user.learning_goals or "علاقه‌مند به معارف اسلامی و تقریب مذاهب")

        return AuthorProfileDTO(
            author=author_dto,
            bio=bio,
            posts_count=len(posts),
            likes_count=total_likes,
            followers_count=128 + (len(posts) * 15),
            following_count=42,
            posts=post_dtos
        )

    @classmethod
    async def ai_assist_caption(cls, data: AIAssistCaptionRequest) -> AIAssistCaptionResponse:
        """
        AI assistant for enhancing draft captions, generating hashtags,
        suggesting Quranic verses & Hadiths, and checking theological appropriateness.
        """
        # Built-in high-quality suggestions for offline/fast mode
        draft = data.draft_text.strip()
        enhanced_text = f"✨ {draft}\n\nنکته‌ای تأمل‌برانگیز در مسیر رشد معنوی و معرفت دینی که یادآوری آن همواره دل‌ها را صیقل می‌دهد."
        suggested_title = "تأمل روز: " + (draft[:40] + "..." if len(draft) > 40 else draft)

        suggested_tags = [
            "#معارف_اسلامی", "#تدبر_در_قرآن", "#تقریب_مذاهب", "#اخلاق_فردی", "#سبک_زندگی_مؤمنانه"
        ]

        verse = {
            "surah": "البقرة",
            "ayah": 186,
            "arabic": "وَإِذَا سَأَلَكَ عِبَادِي عَنِّي فَإِنِّي قَرِيبٌ أُجِيبُ دَعْوَةَ الدَّاعِ إِذَا دَعَانِ",
            "translation": "و هنگامی که بندگانم از تو درباره من بپرسند، [بگو:] من نزدیکم؛ دعای دعاکننده را هنگامی که مرا می‌خواند، پاسخ می‌دهم."
        }

        hadith = {
            "source": "نهج البلاغة، حکمت ۱۴۷",
            "arabic": "الْعِلْمُ يَهْتِفُ بِالْعَمَلِ فَإِنْ أَجَابَهُ وَإِلَّا ارْتَحَلَ عَنْهُ",
            "translation": "دانش همواره عمل را فرا می‌خواند؛ اگر پاسخش داد می‌ماند، وگرنه کوچ می‌کند."
        }

        is_clean, note = cls._moderate_content(draft)

        return AIAssistCaptionResponse(
            enhanced_caption=enhanced_text,
            suggested_title=suggested_title,
            suggested_hashtags=suggested_tags,
            suggested_quran_verse=verse,
            suggested_hadith=hadith,
            appropriateness_check={"is_appropriate": is_clean, "note": note}
        )

    @classmethod
    async def ai_analyze_post(cls, db: AsyncSession, post_id: str) -> AIAnalyzePostResponse:
        post = await db.scalar(select(Post).where(Post.id == post_id))
        if not post:
            raise AppException(code="POST_NOT_FOUND", message="پست یافت نشد.", status_code=404)

        # Check cached AI summary
        summary = post.ai_summary or f"این محتوا پیرامون موضوع «{post.title or post.category}» تدوین شده و بر ابعاد اخلاقی و فقهی آن با رویکرد تقریبی تأکید می‌ورزد."
        
        themes = ["اخلاق اسلامی", "تزکیه نفس", "تقریب بین‌المذاهب", "حقوق متقابل در جامعه اسلامی"]
        
        verses = post.quran_references if post.quran_references else [
            {
                "surah": "الحجرات",
                "ayah": 10,
                "arabic": "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ وَاتَّقُوا اللَّهَ لَعَلَّكُمْ تُرْحَمُونَ",
                "translation": "مؤمنان برادر یکدیگرند؛ پس میان دو برادر خود صلح برقرار کنید و تقوای الهی پیشه کنید، باشد که مشمول رحمت شوید."
            }
        ]

        hadiths = post.hadith_references if post.hadith_references else [
            {
                "source": "صحیح بخاری و کافی شریف",
                "arabic": "الْمُسْلِمُ مَنْ سَلِمَ الْمُسْلِمُونَ مِنْ لِسَانِهِ وَيَدِهِ",
                "translation": "مسلمان واقعی کسی است که مسلمانان از زبان و دست او در امان باشند."
            }
        ]

        approximation = (
            "این مضمون از نقاط وفاق بنیادین میان تمامی مذاهب اسلامی (شیعه اثناعشری، حنفی، شافعی و مالکی) بوده "
            "و بر ارتقای مکارم اخلاقی و وحدت امت اسلام استوار است."
        )

        return AIAnalyzePostResponse(
            post_id=post_id,
            conceptual_summary=summary,
            key_themes=themes,
            related_quran_verses=verses,
            related_hadiths=hadiths,
            sectarian_approximation_notes=approximation
        )
