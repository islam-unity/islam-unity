import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import selectinload

from app.db.models import Ayah, Book, BookChapter, ConsultationThread, ConsultationMessage, KnowledgeChunk
from app.schemas.ai_chat import SourceCitationDTO
from app.services.jev_service import JevService
from app.services.vector_service import VectorService
from app.services.rag_evaluator_service import RAGEvaluatorService
from app.config import settings

logger = logging.getLogger(__name__)


class AgenticRAGService:
    """
    Autonomous Multi-Step Agentic RAG with:
    1. Intent Extraction & Multi-Query Expansion
    2. Hierarchical SQL + Vector Search
    3. Jev Chapter Selection (Choice) & Sufficiency Evaluation (Noul)
    4. Self-Reflection & Retry Loop (Max 2 iterations)
    5. Fallback & Human Scholar Escalation
    6. Clickable Inline Footnote Citations
    """

    @classmethod
    async def run_agentic_retrieval(
        cls,
        db: AsyncSession,
        user_query: str,
        status_callback: Optional[Callable[[str, str], Any]] = None,
        excluded_chunk_ids: Optional[List[str]] = None,
        target_book_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the full agentic loop.
        Calls status_callback(stage, message) during each phase if provided.
        Filters out any chunks in excluded_chunk_ids to prevent duplicates on re-search.
        Optionally constrains retrieval to target_book_id if specified.
        """
        excluded_set = set(excluded_chunk_ids or [])

        # 1. Routing & Query Expansion
        if status_callback:
            await status_callback("ROUTING", "🔍 در حال تشخیص حوزه موضوعی، مذهب و استخراج زوایای مختلف سوال...")

        plan = cls.extract_intent_and_expand_query(user_query)
        retrieved_contexts: List[Dict[str, Any]] = []
        is_sufficient = False
        evaluation_result = {"is_sufficient": False, "confidence": 0.0, "score": 0}

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            if status_callback:
                stage_msg = f"🔍 جستجو در منابع درختی و کتابخانه (تلاش {attempt} از {max_attempts})..."
                await status_callback("SEARCHING", stage_msg)

            # Perform Hierarchical Search (SQL first, then Vector)
            candidate_items = await cls._execute_hierarchical_search(
                db, user_query, plan, attempt, excluded_chunk_ids=list(excluded_set), target_book_id=target_book_id
            )
            # Filter out any candidate matching excluded_set
            filtered_candidates = [
                it for it in candidate_items
                if it.get("id") not in excluded_set and it.get("targetUrl") not in excluded_set
            ]
            retrieved_contexts.extend(filtered_candidates)

            # Deduplicate by unique id
            seen = set()
            deduped = []
            for item in retrieved_contexts:
                uid = item.get("id") or item.get("targetUrl")
                if uid not in seen:
                    seen.add(uid)
                    deduped.append(item)
            retrieved_contexts = deduped

            # Combine evidence text for evaluation
            evidence_text = "\n".join([f"{item.get('title')}: {item.get('excerpt')}" for item in retrieved_contexts[:5]])

            # 2. Self-Reflection & Sufficiency Evaluation with RAGEvaluatorService
            if status_callback:
                await status_callback("EVALUATING", "⚖️ ارزیابی کیفیت و کفایت فقهی/معارفی منابع با ماژول ترکیبی RAG Evaluator...")

            eval_res = await RAGEvaluatorService.evaluate_retrieval_set(user_query, retrieved_contexts)
            is_sufficient = eval_res.get("is_sufficient", False)
            top_relevance = eval_res.get("top_relevance_score", 0.0)

            # Assign evaluated scores to context items for citation metadata
            for ctx_item, eval_item in zip(retrieved_contexts, eval_res.get("evaluated_contexts", [])):
                ctx_item["score"] = eval_item.get("relevance_score")
                ctx_item["relevanceVerdict"] = eval_item.get("verdict")

            if is_sufficient:
                logger.info(f"Context sufficient on attempt {attempt} with relevance {top_relevance}%")
                break

            # If not sufficient and has more attempts, rephrase query
            if attempt < max_attempts:
                if status_callback:
                    await status_callback("RETRYING", "🔄 تطابق کامل حاصل نشد؛ بازنویسی کوئری و جستجوی مجدد در سایر فصول...")
                plan["active_queries"] = plan.get("alternative_angles", [user_query])

        # Check scholar escalation trigger intelligently
        from app.services.recommendation_service import RecommendationService
        routing_assessment = RecommendationService.assess_intent_and_routing_needs(
            query=user_query,
            rag_sufficient=is_sufficient
        )
        suggest_scholar = routing_assessment.get("needs_scholar", False)
        if suggest_scholar and status_callback:
            await status_callback("ESCALATING", "⚠️ عدم احراز قطعیت منبع در کتب سامانه؛ آماده‌سازی گزینه ارجاع به عالم دینی...")

        # Build Citations
        citations, context_prompt = cls._build_citations_and_prompt(retrieved_contexts)

        return {
            "isSufficient": is_sufficient,
            "confidence": round(top_relevance / 100.0, 2),
            "relevanceScore": top_relevance,
            "meanRelevanceScore": eval_res.get("mean_relevance_score", 0.0),
            "hitAt3": eval_res.get("hit_at_3", False),
            "plan": plan,
            "sources": citations,
            "contextPrompt": context_prompt,
            "suggestScholarEscalation": suggest_scholar,
            "escalationCategory": plan.get("category", "احکام شرعی و فقهی"),
            "routingAssessment": routing_assessment
        }

    @classmethod
    def extract_intent_and_expand_query(cls, query: str) -> Dict[str, Any]:
        """
        Parses domain, madhhab, major topic and generates 3 query expansion angles.
        """
        q_lower = query.lower()

        # Madhhab Detection
        madhhab = None
        if "شافع" in q_lower:
            madhhab = "شافعی"
        elif "حنف" in q_lower:
            madhhab = "حنفی"
        elif "جعفر" in q_lower or "شیع" in q_lower:
            madhhab = "شیعه اثناعشری"
        elif "مالک" in q_lower:
            madhhab = "مالکی"
        elif "حنبل" in q_lower:
            madhhab = "حنبلی"

        # Domain Detection
        domain = "GENERAL"
        category = "معارف اسلامی"
        if any(w in q_lower for w in ["آیه", "سوره", "قرآن", "تفسیر"]):
            domain = "QURAN"
            category = "قرآن و تفسیر"
        elif any(w in q_lower for w in ["حدیث", "روایت", "بخاری", "کافی", "مسلم", "پیامبر"]):
            domain = "HADITH"
            category = "حدیث و کلام"
        elif any(w in q_lower for w in ["حکم", "نجس", "طهارت", "حلال", "حرام", "نماز", "فقه", "روزه", "خمس", "وضو"]):
            domain = "FIQH"
            category = "احکام شرعی و فقهی"
        elif any(w in q_lower for w in ["اخلاق", "صبر", "شکر", "توکل", "عرفان"]):
            domain = "ETHICS"
            category = "اخلاق و عرفان"

        # Major topic detection
        major_topic = None
        if any(w in q_lower for w in ["آب", "نجس", "متنجس", "طهارت", "وضو", "غسل"]):
            major_topic = "طهارة"
        elif any(w in q_lower for w in ["نماز", "صلاة"]):
            major_topic = "صلاة"
        elif any(w in q_lower for w in ["صبر", "اخلاق", "فضیلت"]):
            major_topic = "صبر و اخلاق"

        # Adaptive detail level & candidate limit
        is_comprehensive = any(w in q_lower for w in [
            "دقت بیشتر", "منابع بیشتر", "جامع", "پژوهشی", "تفصیلی", "تمام منابع", "بیشتر"
        ])
        candidate_limit = 20 if is_comprehensive else 10
        top_k_final = 5 if is_comprehensive else 3
        min_jev_score = 5 if is_comprehensive else 6

        # Multi-Query Expansion with Cross-Lingual Islamic Fiqh Bridge
        from app.services.cross_lingual_service import CrossLingualService
        expanded_angles = CrossLingualService.generate_multi_angle_queries(
            query=query,
            domain=domain,
            category=category
        )
        clean_q = expanded_angles[0] if expanded_angles else query.replace("؟", "").strip()
        alt_angles = expanded_angles[1:] if len(expanded_angles) > 1 else [
            f"احکام {clean_q}",
            f"شرح و فتوای {clean_q} در {category}"
        ]

        # Re-search / retry detection from user query
        retry_keywords = [
            "دوباره بگرد", "دوباره جستجو کن", "منابع دیگر", "مطالب بیشتر",
            "جستجوی مجدد", "مطالب دیگر", "چیز دیگری", "منابع جدید",
            "اطلاعات بیشتر", "جستجوی دوباره", "منابع متفاوت", "تکراری نباشد"
        ]
        is_retry = any(rw in q_lower for rw in retry_keywords)

        return {
            "domain": domain,
            "category": category,
            "madhhab": madhhab,
            "majorTopic": major_topic,
            "candidateLimit": candidate_limit,
            "topKFinal": top_k_final,
            "minJevScore": min_jev_score,
            "isComprehensive": is_comprehensive,
            "isRetry": is_retry,
            "active_queries": expanded_angles[:2] if not is_retry else alt_angles,
            "alternative_angles": alt_angles
        }

    @classmethod
    async def _execute_hierarchical_search(
        cls,
        db: AsyncSession,
        user_query: str,
        plan: Dict[str, Any],
        attempt_num: int,
        excluded_chunk_ids: Optional[List[str]] = None,
        target_book_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hierarchical retrieval across active cross-lingual query angles:
        1. SQL Exact (Quran & Public Consultations)
        2. Qdrant Multi-Vector Representation Search across active angles
        3. Fast Jev Batch Scoring (evaluating summaries with cross-lingual tolerance)
        4. Full Parent-Document SQL Text Hydration from KnowledgeChunk
        5. Fallback to SQL library or legacy vector search if sparse
        """
        results: List[Dict[str, Any]] = []
        domain = plan.get("domain", "GENERAL")
        madhhab = plan.get("madhhab")
        major_topic = plan.get("majorTopic")
        excluded_set = set(excluded_chunk_ids or [])
        active_queries = plan.get("active_queries") or [user_query]

        # ---------------------------------------------------------------------
        # 1. SQL Layer (Quran & Consultations)
        # ---------------------------------------------------------------------
        # If target_book_id is specified, skip general Quran/Consultation to focus on the target book
        if not target_book_id:
            # 1.1 Quran search if domain is QURAN or general
            if domain in ["QURAN", "GENERAL"]:
                ayah_results = await cls._search_sql_quran(db, user_query, excluded_set=excluded_set)
                results.extend(ayah_results)

            # 1.2 Consultation Threads (Public answered fatwas/questions)
            if domain in ["FIQH", "GENERAL"]:
                thread_results = await cls._search_sql_consultation(db, user_query, excluded_set=excluded_set)
                results.extend(thread_results)

        # ---------------------------------------------------------------------
        # 2. Multi-Vector Representation Search & Jev Batch Scoring
        # ---------------------------------------------------------------------
        candidate_limit = plan.get("candidateLimit", 10)
        top_k_final = plan.get("topKFinal", 3)
        min_jev_score = plan.get("minJevScore", 6)

        # Fan-out search across all active cross-lingual query angles
        all_repr_candidates: List[Dict[str, Any]] = []
        seen_cand_ids = set()

        for q_angle in active_queries:
            sub_candidates = await VectorService.search_by_representations(
                query=q_angle,
                limit_chunks=candidate_limit,
                madhhab=madhhab,
                major_topic=major_topic,
                book_id=target_book_id
            )
            for sc in sub_candidates:
                cid = sc.get("chunkId") or sc.get("id")
                if cid and cid not in seen_cand_ids and cid not in excluded_set:
                    seen_cand_ids.add(cid)
                    all_repr_candidates.append(sc)

        repr_candidates = all_repr_candidates

        if repr_candidates:
            # Batch rerank candidate summaries with Jev
            ranked_chunks = await JevService.batch_rerank_chunks(
                user_query=user_query,
                candidate_chunks=repr_candidates,
                min_score=min_jev_score,
                top_k=top_k_final
            )

            # Hydrate full parent text from SQL KnowledgeChunk
            chunk_ids = [c["chunkId"] for c in ranked_chunks if c.get("chunkId") and c.get("chunkId") not in excluded_set]
            db_chunks = {}
            if chunk_ids:
                q_res = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.id.in_(chunk_ids)))
                db_chunks = {kc.id: kc for kc in q_res.scalars().all()}

            for rc in ranked_chunks:
                cid = rc.get("chunkId")
                if cid in excluded_set:
                    continue
                kc = db_chunks.get(cid)
                full_text = kc.full_text if kc else (rc.get("summary") or "")
                arabic_text = (kc.text_arabic if kc else "") or ""
                excerpt = f"«{arabic_text}»\n{full_text[:400]}" if arabic_text else full_text[:400]
                chunk_lang = getattr(kc, "language", None) or rc.get("language") or "fa"

                results.append({
                    "id": cid,
                    "type": "BOOK",
                    "title": f"{rc.get('bookTitle')} - {rc.get('chapterTitle')}",
                    "targetUrl": f"source://book/{rc.get('bookId', 'bk_1')}/chapter/{cid}",
                    "excerpt": excerpt,
                    "madhhab": rc.get("madhhab"),
                    "pageNumber": rc.get("pageNumber"),
                    "language": chunk_lang,
                    "score": rc.get("score"),
                    "jev_score": rc.get("jev_score")
                })
        else:
            # Fallback to chapter-level search if no chunk representations exist yet
            book_results = await cls._search_sql_library(db, user_query, plan, excluded_set=excluded_set, target_book_id=target_book_id)
            results.extend(book_results)

        # ---------------------------------------------------------------------
        # 3. Fallback to Legacy Vector Search if sparse (< 2 items) or retry attempt
        # ---------------------------------------------------------------------
        if len(results) < 2 or attempt_num > 1:
            vector_hits = await VectorService.search_semantic(
                query=user_query,
                limit=4,
                madhhab=madhhab,
                major_topic=major_topic,
                book_id=target_book_id
            )
            for hit in vector_hits:
                cid = hit.get("chunkId", f"vec_{len(results)}")
                if cid in excluded_set:
                    continue
                results.append({
                    "id": cid,
                    "type": "BOOK",
                    "title": f"{hit.get('bookTitle')} - {hit.get('chapterTitle')}",
                    "targetUrl": f"source://book/{hit.get('bookId', 'bk_1')}/chapter/{hit.get('chunkId', 'ch_1')}",
                    "excerpt": hit.get("text", "")[:280],
                    "madhhab": hit.get("madhhab"),
                    "pageNumber": hit.get("pageNumber"),
                    "language": hit.get("language") or "fa",
                    "score": hit.get("score")
                })

        return results

    @classmethod
    async def _search_sql_quran(cls, db: AsyncSession, query: str, excluded_set: Optional[set] = None) -> List[Dict[str, Any]]:
        keywords = [w.strip() for w in query.replace("؟", "").split() if len(w.strip()) > 2]
        if not keywords:
            return []

        conditions = [or_(Ayah.text_clean.ilike(f"%{kw}%"), Ayah.text_persian.ilike(f"%{kw}%")) for kw in keywords[:3]]
        stmt = select(Ayah).where(or_(*conditions)).limit(3)
        res = await db.execute(stmt)
        ayahs = res.scalars().all()

        results = []
        for a in ayahs:
            aid = f"ayah_{a.surah_id}_{a.ayah_number}"
            if excluded_set and (aid in excluded_set or str(a.id) in excluded_set):
                continue
            results.append({
                "id": aid,
                "type": "QURAN",
                "title": f"قرآن کریم، سوره {a.surah_id}، آیه {a.ayah_number}",
                "targetUrl": f"source://quran/surah/{a.surah_id}/ayah/{a.ayah_number}",
                "excerpt": f"«{a.text_arabic}» - ترجمه: {a.text_persian}",
                "pageNumber": a.page_number,
                "language": "ar"
            })
        return results

    @classmethod
    async def _search_sql_consultation(cls, db: AsyncSession, query: str, excluded_set: Optional[set] = None) -> List[Dict[str, Any]]:
        keywords = [w.strip() for w in query.replace("؟", "").split() if len(w.strip()) > 2]
        if not keywords:
            return []

        conditions = [ConsultationThread.title.ilike(f"%{kw}%") for kw in keywords[:2]]
        stmt = select(ConsultationThread).options(
            selectinload(ConsultationThread.messages)
        ).where(ConsultationThread.is_public == True, or_(*conditions)).limit(2)

        res = await db.execute(stmt)
        threads = res.scalars().all()

        results = []
        for t in threads:
            if excluded_set and t.id in excluded_set:
                continue
            last_msg = t.messages[-1].text if t.messages else t.title
            results.append({
                "id": t.id,
                "type": "CONSULTATION",
                "title": f"استفتاء: {t.title}",
                "targetUrl": f"source://consultation/thread/{t.id}",
                "excerpt": last_msg[:250],
                "madhhab": None,
                "language": "fa"
            })
        return results

    @classmethod
    async def _search_sql_library(
        cls,
        db: AsyncSession,
        query: str,
        plan: Dict[str, Any],
        excluded_set: Optional[set] = None,
        target_book_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # Fetch books matching category or madhhab or target_book_id
        if target_book_id:
            stmt = select(Book).options(selectinload(Book.chapters)).where(Book.id == target_book_id)
        else:
            stmt = select(Book).options(selectinload(Book.chapters))
        madhhab = plan.get("madhhab")

        res = await db.execute(stmt)
        books = res.scalars().all()

        results = []
        for book in books:
            # Check madhhab filter if specified
            if not target_book_id and madhhab and madhhab not in (book.tags or []):
                continue

            chapters = book.chapters
            if not chapters:
                continue

            # Pinpoint the single most relevant chapter using Jev
            chapter_titles = [ch.title for ch in chapters]
            best_chapter_title = await JevService.select_chapter(query, chapter_titles, book.title)

            matched_chapter = next((ch for ch in chapters if ch.title == best_chapter_title), chapters[0])

            if excluded_set and (matched_chapter.id in excluded_set or book.id in excluded_set):
                continue

            # Check if chapter has content matching query keywords
            keywords = [w.strip() for w in query.replace("؟", "").split() if len(w.strip()) > 2]
            match_found = any(kw in matched_chapter.content for kw in keywords) or (best_chapter_title != chapters[0].title)

            if match_found:
                results.append({
                    "id": matched_chapter.id,
                    "type": "BOOK",
                    "title": f"{book.title} ({matched_chapter.title})",
                    "targetUrl": f"source://book/{book.id}/chapter/{matched_chapter.id}",
                    "excerpt": matched_chapter.content[:280] + "...",
                    "madhhab": madhhab,
                    "pageNumber": matched_chapter.chapter_number,
                    "language": getattr(book, "language", "fa") or "fa"
                })

        return results

    @classmethod
    def _build_citations_and_prompt(
        cls,
        retrieved_contexts: List[Dict[str, Any]]
    ) -> Tuple[List[SourceCitationDTO], str]:
        """
        Creates numbered citation DTOs and formats context for LLM prompt.
        """
        citations = []
        prompt_lines = []

        for idx, item in enumerate(retrieved_contexts[:4], start=1):
            citation = SourceCitationDTO(
                index=idx,
                type=item.get("type", "BOOK"),
                title=item.get("title", f"منبع {idx}"),
                targetUrl=item.get("targetUrl", f"source://item/{idx}"),
                excerpt=item.get("excerpt"),
                madhhab=item.get("madhhab"),
                pageNumber=item.get("pageNumber"),
                score=item.get("score"),
                language=item.get("language") or "fa"
            )
            citations.append(citation)

            prompt_lines.append(
                f"[{idx}] منبع: {citation.title}\n"
                f"پیوند کلیک: {citation.targetUrl}\n"
                f"متن شواهد: {citation.excerpt}\n"
            )

        context_prompt = "\n---\n".join(prompt_lines) if prompt_lines else "منبع مستقیم مستندی در سامانه یافت نشد."
        return citations, context_prompt

