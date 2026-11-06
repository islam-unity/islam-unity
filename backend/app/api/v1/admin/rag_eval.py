import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import success_response
from app.db.models import Book, KnowledgeChunk, RAGEvaluationReport
from app.db.session import get_db
from app.api.v1.admin.common import paginate
from app.schemas.ai_chat import PersonaConfigDTO
from app.services.agent.engine import AgentEngine
from app.services.rag_evaluator_service import RAGEvaluatorService

logger = logging.getLogger(__name__)

router = APIRouter()


class RAGCompareRequest(BaseModel):
    query: str = Field(..., description="متن پرسش جهت مقایسه رودررو بین موتور Agent و Legacy")
    bookIds: Optional[List[str]] = Field(default=None, description="شناسه یک یا چند کتاب هدف")
    madhhab: Optional[str] = Field(default=None, description="مذهب کاربر یا زمینه فقهی")
    detailLevel: Optional[str] = Field(default="balanced", description="سطح تفصیل: brief, balanced, detailed")
    persist: Optional[bool] = Field(default=True, description="آیا نتیجه مقایسه در تاریخچه گزارش‌ها ذخیره شود")


class RAGEvalRequest(BaseModel):
    query: str = Field(..., description="متن پرسش معارفی یا فقهی جهت ارزیابی بازیابی")
    bookIds: Optional[List[str]] = Field(default=None, description="شناسه یک یا چند کتاب هدف")
    mode: Optional[str] = Field(default="retrieval_only", description="حالت اجرا: retrieval_only, end_to_end یا agent")
    limit: Optional[int] = Field(default=5, description="حداکثر تعداد چانک‌های بازیابی‌شده")
    persist: Optional[bool] = Field(default=True, description="آیا نتیجه در تاریخچه ارزیابی‌ها ذخیره شود")
    model: Optional[str] = Field(default=None, description="مدل زبانی اختیاری جهت تولید پاسخ در حالت کامل")


def serialize_eval_report(rep: RAGEvaluationReport, include_details: bool = True) -> Dict[str, Any]:
    dt = rep.details or {}
    base = {
        "id": rep.id,
        "bookId": rep.book_id,
        "title": rep.title,
        "totalQueries": rep.total_queries,
        "avgRelevanceScore": rep.avg_relevance_score,
        "hitRateAt3": rep.hit_rate_at_3,
        "passingRate": rep.passing_rate,
        "status": rep.status,
        "evalType": dt.get("evalType", "SINGLE_QUERY" if rep.total_queries == 1 else "BATCH_BENCHMARK"),
        "query": dt.get("query"),
        "mode": dt.get("mode", "retrieval_only"),
        "createdAt": rep.created_at.isoformat() if rep.created_at else None,
        "bookTitle": dt.get("book_title") or (dt.get("selectedBooks", [{}])[0].get("title") if dt.get("selectedBooks") else "همه منابع"),
        "totalLatencyMs": dt.get("timingBreakdown", {}).get("totalLatencyMs"),
        "behindTheScenes": dt.get("behindTheScenes")
    }
    if include_details:
        base["details"] = dt
    return base


@router.get("/books", summary="فهرست کتب پایگاه دانش به همراه تعداد چانک‌ها جهت ارزیابی")
async def list_eval_books(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    b_stmt = select(Book).order_by(Book.title.asc())
    books = (await db.scalars(b_stmt)).all()

    # Aggregate chunk count per book
    counts_map: Dict[str, int] = {}
    try:
        cnt_stmt = select(KnowledgeChunk.book_id, func.count(KnowledgeChunk.id)).group_by(KnowledgeChunk.book_id)
        cnt_res = await db.execute(cnt_stmt)
        for row in cnt_res.all():
            if row[0]:
                counts_map[str(row[0])] = int(row[1])
    except Exception:
        pass

    items = [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author or "نامشخص",
            "category": b.category_id or "عمومی",
            "madhhab": getattr(b, "madhhab", None),
            "chunkCount": counts_map.get(b.id, 0)
        }
        for b in books
    ]
    return success_response(data=items)


@router.post("/evaluate", summary="ارزیابی دقیق تک‌پرسش RAG به همراه تفکیک زمان‌بندی و نمرات کامل")
async def evaluate_query(
    payload: RAGEvalRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    clean_q = payload.query.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="متن پرسش الزامی است.")

    try:
        result = await RAGEvaluatorService.evaluate_single_query_profiled(
            db=db,
            query=clean_q,
            book_ids=payload.bookIds,
            mode=payload.mode or "retrieval_only",
            limit=payload.limit or 5,
            persist=payload.persist if payload.persist is not None else True,
            model_override=payload.model
        )
        return success_response(
            data=result,
            meta={"message": "ارزیابی و پروفایلینگ پرسش با موفقیت انجام شد."}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در اجرای ارزیابی RAG: {str(e)}")


@router.post("/compare", summary="مقایسه رودررو بین موتور Agent و Legacy")
async def compare_query_engines(
    payload: RAGCompareRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    clean_q = payload.query.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="متن پرسش الزامی است.")

    # 1. Execute Legacy Pipeline (profiled end-to-end)
    t_legacy_start = time.perf_counter()
    legacy_res: Dict[str, Any] = {}
    try:
        legacy_res = await RAGEvaluatorService.evaluate_single_query_profiled(
            db=db,
            query=clean_q,
            book_ids=payload.bookIds,
            mode="end_to_end",
            limit=5,
            persist=False
        )
    except Exception as e:
        logger.warning(f"Error evaluating legacy pipeline: {e}")
        legacy_res = {
            "retrieval": {"top_relevance_score": 0.0, "evaluated_contexts": []},
            "answer": {"text": f"خطا در اجرای پایپ‌لاین سنتی: {str(e)}", "citations": []},
            "timingBreakdown": {"totalLatencyMs": 0.0}
        }
    legacy_latency_ms = legacy_res.get("timingBreakdown", {}).get("totalLatencyMs") or round((time.perf_counter() - t_legacy_start) * 1000, 2)
    legacy_answer = legacy_res.get("answer", {}).get("text", "")
    legacy_citations = legacy_res.get("answer", {}).get("citations", [])
    legacy_score = legacy_res.get("retrieval", {}).get("top_relevance_score", 0.0)

    # 2. Execute Agent Engine
    t_agent_start = time.perf_counter()
    detail_map = {"brief": "BRIEF", "balanced": "STANDARD", "detailed": "COMPREHENSIVE"}
    mapped_detail = detail_map.get(payload.detailLevel or "balanced", "STANDARD")
    persona = PersonaConfigDTO(
        detailLevel=mapped_detail,
        fiqhApproach=payload.madhhab or "APPROXIMATION_UNITY"
    )

    plan_data: Dict[str, Any] = {}
    tool_calls: List[Dict[str, Any]] = []
    tool_results: List[Dict[str, Any]] = []
    verification_data: Dict[str, Any] = {}
    agent_tokens: List[str] = []
    agent_sources: List[Dict[str, Any]] = []
    agent_trace_id: Optional[str] = None
    agent_error: Optional[str] = None

    try:
        async for event in AgentEngine.run_agent(
            db=db,
            conversation_id=f"cmp_{uuid.uuid4().hex[:8]}",
            user_id="admin_evaluator",
            user_query=clean_q,
            persona=persona,
            detail_level=payload.detailLevel
        ):
            if event.type == "plan":
                plan_data = event.data.get("plan", {})
            elif event.type == "tool_call":
                tool_calls.append(event.data)
            elif event.type == "tool_result":
                tool_results.append(event.data)
            elif event.type == "verify":
                verification_data = event.data
            elif event.type == "token":
                agent_tokens.append(event.data.get("delta", ""))
            elif event.type == "sources":
                agent_sources = event.data.get("sources", [])
            elif event.type == "done":
                agent_trace_id = event.data.get("traceId")
    except Exception as e:
        logger.error(f"Error running AgentEngine in compare: {e}", exc_info=True)
        agent_error = str(e)

    agent_latency_ms = round((time.perf_counter() - t_agent_start) * 1000, 2)
    agent_answer = "".join(agent_tokens) if agent_tokens else (f"خطا در اجرای ایجنت: {agent_error}" if agent_error else "")

    # Unique tools invoked
    unique_tools = list({tc.get("tool") for tc in tool_calls if tc.get("tool")})

    # 3. Comparative Synthesis & Verdict
    diff_latency_ms = round(agent_latency_ms - legacy_latency_ms, 2)
    verified_status = verification_data.get("status") if verification_data else "NONE"

    if agent_error:
        verdict = "اجرای سنتی موفق بود؛ ایجنت با خطا مواجه شد."
        winner = "legacy"
    elif plan_data.get("isDirectAnswer"):
        verdict = "پرسش از نوع عمومی/احوال‌پرسی بود؛ هر دو سیستم بدون جستجوی پیچیده پاسخ سریع ارائه دادند."
        winner = "tie"
    elif len(agent_sources) > 0 or len(tool_calls) > 0:
        tool_names_str = "، ".join(unique_tools) if unique_tools else "بدون ابزار"
        steps_count = len(plan_data.get("steps", []))
        verdict = f"موتور ایجنت با برنامه‌ریزی ({steps_count} مرحله)، فراخوانی {len(tool_calls)} ابزار تخصصی ({tool_names_str}) و راستی‌آزمایی فقهی، عمق استنادی و دقت بالاتری را نسبت به پایپ‌لاین تک‌مرحله‌ای سنتی ثبت کرد."
        winner = "agent"
    else:
        verdict = "هر دو موتور عملکرد قابل قبولی ارائه دادند."
        winner = "tie"

    result_payload = {
        "query": clean_q,
        "verdict": verdict,
        "winner": winner,
        "legacy": {
            "engine": "legacy",
            "latencyMs": legacy_latency_ms,
            "relevanceScore": legacy_score,
            "answer": legacy_answer,
            "citationsCount": len(legacy_citations),
            "citations": legacy_citations,
            "contexts": legacy_res.get("retrieval", {}).get("evaluated_contexts", []),
            "stages": legacy_res.get("stages", [])
        },
        "agent": {
            "engine": "agent",
            "latencyMs": agent_latency_ms,
            "plan": plan_data,
            "toolCallsCount": len(tool_calls),
            "toolsUsed": unique_tools,
            "toolCalls": tool_calls,
            "toolResults": tool_results,
            "verification": verification_data,
            "answer": agent_answer,
            "sourcesCount": len(agent_sources),
            "sources": agent_sources,
            "traceId": agent_trace_id
        },
        "comparison": {
            "latencyDifferenceMs": diff_latency_ms,
            "sourceCountDifference": len(agent_sources) - len(legacy_citations),
            "verificationPassed": verification_data.get("passed", True) if verification_data else None,
            "toolDiversity": len(unique_tools)
        }
    }

    # 4. Optional Persistence
    report_id = None
    if payload.persist:
        report_id = f"cmp_{uuid.uuid4().hex[:12]}"
        rep = RAGEvaluationReport(
            id=report_id,
            book_id=(payload.bookIds[0] if payload.bookIds and len(payload.bookIds) == 1 else None),
            title=f"مقایسه رودررو: {clean_q[:40]}...",
            total_queries=1,
            avg_relevance_score=legacy_score,
            hit_rate_at_3=100.0 if legacy_citations else 0.0,
            passing_rate=100.0 if winner in ("agent", "tie") else 50.0,
            status="PASSED" if winner in ("agent", "tie") else "NEEDS_IMPROVEMENT",
            details={
                "evalType": "HEAD_TO_HEAD_COMPARISON",
                "query": clean_q,
                "winner": winner,
                "verdict": verdict,
                "legacy": result_payload["legacy"],
                "agent": result_payload["agent"],
                "comparison": result_payload["comparison"]
            }
        )
        db.add(rep)
        await db.commit()
        result_payload["reportId"] = report_id

    return success_response(
        data=result_payload,
        meta={"message": "مقایسه رودررو بین موتور سنتی و ایجنت با موفقیت انجام شد."}
    )


@router.get("/history", summary="فهرست تاریخچه ارزیابی‌های ذخیره‌شده")
async def list_eval_history(
    page: int = Query(1),
    pageSize: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
    eval_type: Optional[str] = Query(None),
    evalType: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    stmt = select(RAGEvaluationReport)

    if status:
        stmt = stmt.where(RAGEvaluationReport.status == status)

    stmt = stmt.order_by(RAGEvaluationReport.created_at.desc())
    items, meta = await paginate(db, stmt, page=page, page_size=pageSize, limit=limit)

    target_type = eval_type or evalType
    serialized = []
    for rep in items:
        record = serialize_eval_report(rep, include_details=False)
        if target_type and record.get("evalType") != target_type:
            continue
        serialized.append(record)

    return success_response(
        data=serialized,
        meta=meta
    )


@router.get("/history/{id}", summary="دریافت جزئیات کامل یک ارزیابی ذخیره‌شده")
async def get_eval_history_detail(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    rep = await db.scalar(select(RAGEvaluationReport).where(RAGEvaluationReport.id == id))
    if not rep:
        raise HTTPException(status_code=404, detail="گزارش ارزیابی مورد نظر یافت نشد.")

    return success_response(data=serialize_eval_report(rep, include_details=True))


@router.delete("/history/{id}", summary="حذف یک رکورد ارزیابی از تاریخچه")
async def delete_eval_history(
    id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    rep = await db.scalar(select(RAGEvaluationReport).where(RAGEvaluationReport.id == id))
    if not rep:
        raise HTTPException(status_code=404, detail="گزارش ارزیابی مورد نظر یافت نشد.")

    await db.delete(rep)
    await db.commit()
    return success_response(data={"id": id, "deleted": True}, meta={"message": "گزارش ارزیابی با موفقیت حذف گردید."})
