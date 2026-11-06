import time
import uuid
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import AgentTrace, User, PersonaConfig
from app.schemas.ai_chat import PersonaConfigDTO, SourceCitationDTO
from app.services.llm_provider_service import LLMProviderService
from app.services.agent.budget import BudgetManager
from app.services.agent.events import AgentEvent, AgentEventType
from app.services.agent.planner import AgentPlanner, AgentPlan
from app.services.agent.executor import AgentExecutor
from app.services.agent.verifier import AgentVerifier
from app.services.agent.memory import MemoryService
from app.services.agent.tools import get_default_chat_tools_registry
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class AgentEngine:
    """
    Main Agent Orchestrator:
    Executes the full Think -> Plan -> ReAct Tools -> Verify cycle,
    yielding structured streaming events and saving an auditable AgentTrace.
    """

    @classmethod
    async def run_agent(
        cls,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        user_query: str,
        persona: PersonaConfigDTO,
        detail_level: Optional[str] = None,
        target_language: Optional[str] = None,
        exclude_previous_sources: Optional[bool] = None,
        target_book_id: Optional[str] = None,
        target_scholar_id: Optional[str] = None
    ) -> AsyncGenerator[AgentEvent, None]:
        t_engine_start = time.perf_counter()
        trace_id = f"tr_{uuid.uuid4().hex[:12]}"

        # 1. Load Memory and Context
        mem_context = await MemoryService.get_user_memory_context(db, user_id)
        conv_history = await MemoryService.get_conversation_history(db, conversation_id, limit_recent=6)
        
        excluded_ids = []
        if exclude_previous_sources:
            excluded_ids = await MemoryService.get_previous_source_ids(db, conversation_id)

        # 2. Resolve Budget
        extra_cfg = (await LLMProviderService.get_section_config(db, "agent_executor")).get("extra_params", {})
        budget = BudgetManager.resolve_budget(
            detail_level=detail_level or persona.detailLevel,
            user_query=user_query,
            extra_params=extra_cfg
        )

        registry = get_default_chat_tools_registry()

        # 3. Planner Phase
        plan = await AgentPlanner.create_plan(
            user_query=user_query,
            persona=persona,
            conversation_history=conv_history,
            memory_context=mem_context,
            available_tool_names=registry.list_names(),
            db=db
        )

        yield AgentEvent(
            type=AgentEventType.PLAN.value,
            data={"plan": plan.to_dict()}
        )

        # Direct Answer path (e.g. greetings, simple conversation)
        if plan.is_direct_answer:
            direct_messages = [
                {
                    "role": "system",
                    "content": f"تو {persona.botName or 'دستیار معارفی اتحاد'} هستی با لحن {persona.tone or 'دوستانه'}. پاسخ کوتاه، صمیمی و محترمانه بده."
                },
                {"role": "user", "content": user_query}
            ]
            direct_res = await LLMProviderService.call_chat_with_tools(
                section_key="chat",
                messages=direct_messages,
                tools=None,
                db=db,
                temperature=0.7,
                user_id=user_id,
                conversation_id=conversation_id
            )
            full_text = direct_res.get("text", "") if direct_res else "درود و احترام، در خدمت شما هستم."
            
            # Stream tokens
            for chunk in full_text.split(" "):
                yield AgentEvent(type=AgentEventType.TOKEN.value, data={"delta": chunk + " "})
                await asyncio.sleep(0.01)

            yield AgentEvent(
                type=AgentEventType.SOURCES.value,
                data={"sources": [], "suggestScholarEscalation": False}
            )

            latency_ms = round((time.perf_counter() - t_engine_start) * 1000, 2)
            # Save Trace
            await cls._save_trace(
                db=db,
                trace_id=trace_id,
                conversation_id=conversation_id,
                user_id=user_id,
                user_query=user_query,
                plan=plan.to_dict(),
                tool_calls=[],
                verification={"verdict": "DIRECT_ANSWER"},
                total_latency_ms=latency_ms,
                total_tokens=direct_res.get("usage", {}).get("totalTokens", 20) if direct_res else 20
            )

            yield AgentEvent(
                type=AgentEventType.DONE.value,
                data={
                    "traceId": trace_id,
                    "fullText": full_text,
                    "totalLatencyMs": latency_ms
                }
            )
            return

        # 4. Executor Phase (ReAct loop)
        async def event_emitter(ev: AgentEvent):
            pass  # Buffer or yield callback

        event_queue = asyncio.Queue()

        async def on_executor_event(ev: AgentEvent):
            await event_queue.put(ev)

        # Run Executor
        exec_task = asyncio.create_task(
            AgentExecutor.run(
                user_query=user_query,
                plan=plan,
                budget=budget,
                registry=registry,
                persona=persona,
                conversation_history=conv_history,
                memory_context=mem_context,
                excluded_source_ids=excluded_ids,
                event_callback=on_executor_event,
                db=db,
                user_id=user_id,
                conversation_id=conversation_id
            )
        )

        while not exec_task.done():
            while not event_queue.empty():
                ev = await event_queue.get()
                yield ev
            await asyncio.sleep(0.03)

        # Drain remaining events
        while not event_queue.empty():
            ev = await event_queue.get()
            yield ev

        exec_res = await exec_task
        draft_answer = exec_res.get("draftAnswer", "")
        sources: List[SourceCitationDTO] = exec_res.get("sources", [])
        tool_traces = exec_res.get("toolTraces", [])

        # 5. Verifier Phase
        verification = await AgentVerifier.verify_and_refine(
            draft_answer=draft_answer,
            sources=sources,
            user_query=user_query,
            target_madhhab=plan.target_madhhab,
            db=db
        )

        yield AgentEvent(
            type=AgentEventType.VERIFY.value,
            data={
                "verdict": verification.verdict,
                "issues": verification.issues_found,
                "citationCheckPassed": verification.citation_check_passed,
                "rulingsVerified": verification.rulings_verified
            }
        )

        # Ensure final_answer is the actual LLM answer, never internal agent critique/thoughts
        final_answer = draft_answer
        candidate = (verification.corrected_answer or "").strip()
        if candidate and candidate != draft_answer:
            critique_markers = [
                "به جای", "باید", "لازم است", "پیشنهاد می‌شود", "پیشنهاد می شود",
                "اصلاح شود", "حذف شود", "اصلاح گردد", "تطبیق داده شود",
                "ارجاع داده شود", "منابع نامرتبط", "استفاده شود"
            ]
            is_critique = any(marker in candidate[:70] for marker in critique_markers)
            if not is_critique and len(candidate) > 100:
                final_answer = candidate

        # If answer was flagged and no sources exist for fiqh query, append general-knowledge disclaimer
        if plan.requires_citations and len(sources) == 0:
            final_answer += "\n\n*(توجه: این پاسخ بر اساس دانش عمومی تدوین شده و فاقد استناد مستقیم به کتب سامانه است.)*"

        # 6. Stream Final Verified Tokens
        words = final_answer.split(" ")
        for idx, w in enumerate(words):
            yield AgentEvent(
                type=AgentEventType.TOKEN.value,
                data={"delta": w + (" " if idx < len(words) - 1 else "")}
            )
            await asyncio.sleep(0.015)

        # 7. Resolve Scholar and Book Recommendations based on intelligent routing assessment
        routing_info = await RecommendationService.get_routing_verdict(
            query=user_query,
            db=db,
            target_scholar_id=target_scholar_id,
            target_book_id=target_book_id
        )
        rec_scholar = routing_info.get("recommendedScholar")
        rec_book = routing_info.get("recommendedBook")
        ai_capability = routing_info.get("ai_capability_status", "SELF_SUFFICIENT")

        # Emit Sources & Metadata with Scholar/Book recommendations
        yield AgentEvent(
            type=AgentEventType.SOURCES.value,
            data={
                "sources": [s.model_dump() for s in sources],
                "suggestScholarEscalation": routing_info.get("needs_scholar", False),
                "escalationCategory": exec_res.get("escalationCategory"),
                "recommendedScholar": rec_scholar,
                "recommendedBook": rec_book,
                "aiCapabilityStatus": ai_capability,
                "routingAssessment": routing_info,
                "targetLanguage": target_language or "fa"
            }
        )

        total_latency_ms = round((time.perf_counter() - t_engine_start) * 1000, 2)

        # 8. Persist Auditable AgentTrace in DB
        await cls._save_trace(
            db=db,
            trace_id=trace_id,
            conversation_id=conversation_id,
            user_id=user_id,
            user_query=user_query,
            plan=plan.to_dict(),
            tool_calls=tool_traces,
            verification={
                "verdict": verification.verdict,
                "issues": verification.issues_found,
                "citationCheckPassed": verification.citation_check_passed
            },
            total_latency_ms=total_latency_ms,
            total_tokens=150 * (len(tool_traces) + 1)
        )

        yield AgentEvent(
            type=AgentEventType.DONE.value,
            data={
                "traceId": trace_id,
                "fullText": final_answer,
                "totalLatencyMs": total_latency_ms
            }
        )

        # 9. Non-blocking Background Long-term Memory Extraction
        asyncio.create_task(
            MemoryService.extract_and_persist_memory(
                db=db,
                user_id=user_id,
                conversation_id=conversation_id,
                user_message=user_query,
                assistant_reply=final_answer
            )
        )

    @classmethod
    async def _save_trace(
        cls,
        db: AsyncSession,
        trace_id: str,
        conversation_id: str,
        user_id: Optional[str],
        user_query: str,
        plan: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        verification: Dict[str, Any],
        total_latency_ms: float,
        total_tokens: int
    ):
        try:
            trace = AgentTrace(
                id=trace_id,
                conversation_id=conversation_id,
                user_id=user_id,
                user_query=user_query,
                mode="agent",
                plan=plan,
                tool_calls=tool_calls,
                verification=verification,
                total_latency_ms=total_latency_ms,
                total_tokens=total_tokens,
                estimated_cost_usd=round((total_tokens / 1_000_000.0) * 0.20, 6)
            )
            db.add(trace)
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not persist AgentTrace: {e}")
