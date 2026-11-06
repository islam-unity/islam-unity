import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.db.models import ConsultationThread
from app.services.agent.tools.registry import ToolSpec

logger = logging.getLogger(__name__)


async def tool_search_consultations(
    query: str,
    limit: int = 3,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Searches answered public consultation threads and fatwas from certified scholars.
    """
    if db is None or not query:
        return []

    clean_q = query.replace("؟", "").strip()
    keywords = [w.strip() for w in clean_q.split() if len(w.strip()) > 2]
    if not keywords:
        keywords = [clean_q]

    conditions = [ConsultationThread.title.ilike(f"%{kw}%") for kw in keywords[:3]]

    stmt = (
        select(ConsultationThread)
        .options(selectinload(ConsultationThread.messages))
        .where(ConsultationThread.is_public == True, or_(*conditions))
        .limit(limit)
    )

    res = await db.execute(stmt)
    threads = res.scalars().all()

    results = []
    for t in threads:
        answer_text = ""
        for m in reversed(t.messages):
            if m.sender_role in ("SCHOLAR", "ADMIN"):
                answer_text = m.text
                break
        if not answer_text and t.messages:
            answer_text = t.messages[-1].text

        results.append({
            "threadId": t.id,
            "title": t.title,
            "category": t.category,
            "excerpt": answer_text[:350],
            "isAnswered": t.status == "ANSWERED"
        })

    return results


async def tool_escalate_to_scholar(
    reason: str,
    question_draft: str,
    category: Optional[str] = "احکام شرعی و فقهی",
    **kwargs
) -> Dict[str, Any]:
    """
    Generates a structured recommendation to refer the question to human religious scholars
    when certainty cannot be attained from available system sources.
    (This drafts the recommendation only and does NOT automatically submit a ticket).
    """
    return {
        "escalate": True,
        "category": category or "احکام شرعی و فقهی",
        "reason": reason,
        "questionDraft": question_draft,
        "advice": "با توجه به عدم قطعیت یا پیچیدگی مسئله، توصیه می‌شود کاربر سوال را در بخش مشاوره دینی برای بررسی اساتید و علما ارسال نماید."
    }


SEARCH_CONSULTATIONS_TOOL = ToolSpec(
    name="search_consultations",
    description="جستجو در آرشیو استفتائات و پاسخ‌های مشاوران دینی و علمای سامانه",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "عبارت یا موضوع سوال جهت جستجو در پاسخ‌های علما"
            },
            "limit": {
                "type": "integer",
                "description": "حداکثر تعداد پاسخ‌های استخراج‌شده (پیش‌فرض: 3)",
                "default": 3
            }
        },
        "required": ["query"]
    },
    func=tool_search_consultations,
    summarizer=lambda args, res: f"استخراج {len(res)} پاسخ از استفتائات علمای سامانه"
)

ESCALATE_TO_SCHOLAR_TOOL = ToolSpec(
    name="escalate_to_scholar",
    description="پیشنهاد ارجاع سوال به اساتید و علمای بخش مشاوره هنگام عدم احراز قطعیت منبع یا مسائل اجتهادی مستحدثه",
    parameters={
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "description": "دلیل ضرورت ارجاع (مثلاً عدم یافتن نص صریح، اختلاف فتاوا، یا مسئله مستحدثه)"
            },
            "question_draft": {
                "type": "string",
                "description": "متن ویرایش‌شده و منقح سوال جهت ارسال به بخش مشاوره"
            },
            "category": {
                "type": "string",
                "description": "حوزه موضوعی مسئله (مثلاً فقهی، عقیدتی، خانواده)",
                "default": "احکام شرعی و فقهی"
            }
        },
        "required": ["reason", "question_draft"]
    },
    func=tool_escalate_to_scholar,
    summarizer=lambda args, res: f"پیشنهاد ارجاع به عالم دینی: {args.get('reason', '')[:35]}"
)


async def tool_recommend_scholar_and_book(
    query: str,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Identifies and recommends the most specialized religious scholar and relevant library book
    based on the exact subject matter, expertise domain, and context of the user question.
    """
    from app.services.recommendation_service import RecommendationService
    scholar, book = await RecommendationService.recommend_scholar_and_book(query=query, db=db)
    return {
        "recommendedScholar": scholar,
        "recommendedBook": book
    }


RECOMMEND_SCHOLAR_AND_BOOK_TOOL = ToolSpec(
    name="recommend_scholar_and_book",
    description="پیشنهاد هوشمند و دقیق عالم دینی متخصص و کتاب معارفی مرتبط بر مبنای تخصص، سوابق و زمینه موضوعی پرسش کاربر",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "عبارت یا موضوع سوال جهت تطبیق تخصص عالم و کتاب"
            }
        },
        "required": ["query"]
    },
    func=tool_recommend_scholar_and_book,
    summarizer=lambda args, res: f"پیشنهاد عالم: {res.get('recommendedScholar', {}).get('name', 'عالم معارفی')} و کتاب: {res.get('recommendedBook', {}).get('title', 'کتاب')}"
)

