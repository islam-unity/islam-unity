import asyncio
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import KnowledgeChunk
from app.services.vector_service import VectorService
from app.services.agent.tools.registry import ToolSpec

logger = logging.getLogger(__name__)

ALL_MADHHABS = ["شافعی", "حنفی", "شیعه اثناعشری", "مالکی", "حنبلی"]


async def tool_compare_madhhabs(
    topic: Optional[str] = None,
    madhhabs: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Performs comparative jurisprudential research across Sunni and Shia schools of thought
    for a given topic, retrieving primary sources and rulings for each school.
    """
    effective_topic = topic or kwargs.get("query") or kwargs.get("subject") or kwargs.get("question") or "احکام شرعی"
    target_madhhabs = madhhabs or ALL_MADHHABS
    results_by_madhhab: Dict[str, List[Dict[str, Any]]] = {}

    async def _fetch_for_school(m: str):
        try:
            chunks = await VectorService.search_by_representations(
                query=effective_topic,
                limit_chunks=4,
                madhhab=m
            )
            if not chunks:
                chunks = await VectorService.search_semantic(
                    query=effective_topic,
                    limit=2,
                    madhhab=m
                )
            
            items = []
            for c in chunks[:2]:
                items.append({
                    "bookTitle": c.get("bookTitle", "منبع فقهی"),
                    "chapterTitle": c.get("chapterTitle", ""),
                    "excerpt": (c.get("summary") or c.get("text") or c.get("excerpt") or "")[:300],
                    "pageNumber": c.get("pageNumber")
                })
            return m, items
        except Exception as e:
            logger.debug(f"Error fetching for madhhab {m}: {e}")
            return m, []

    tasks = [_fetch_for_school(m) for m in target_madhhabs]
    gathered = await asyncio.gather(*tasks)

    for m, items in gathered:
        results_by_madhhab[m] = items

    return {
        "topic": topic,
        "comparedSchools": list(results_by_madhhab.keys()),
        "schoolFindings": results_by_madhhab,
        "note": "پژوهش تطبیقی بر پایه مستندات کتب فقهی مذاهب اسلامی بدون ترجیح مذهبی بر مذهب دیگر."
    }


COMPARE_MADHHABS_TOOL = ToolSpec(
    name="compare_madhhabs",
    description="مقایسه تطبیقی و فقه المقارن میان مذاهب اسلامی (شیعه اثناعشری، شافعی، حنفی، مالکی، حنبلی) درباره یک مسئله",
    parameters={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "موضوع یا مسئله فقهی مورد مقایسه (مثلاً مسح سر در وضو، اوقات نماز، سجود سهو)"
            },
            "madhhabs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "لیست مذاهب مد نظر جهت مقایسه (پیش‌فرض: همه مذاهب)"
            }
        },
        "required": ["topic"]
    },
    func=tool_compare_madhhabs,
    summarizer=lambda args, res: f"مقایسه تطبیقی آرای {len(res.get('comparedSchools', []))} مذهب در موضوع «{args.get('topic', '')[:25]}»"
)
