import time
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_chat import SourceCitationDTO, PersonaConfigDTO
from app.services.llm_provider_service import LLMProviderService
from app.services.agent.budget import AgentBudgetConfig
from app.services.agent.planner import AgentPlan
from app.services.agent.events import AgentEvent, AgentEventType
from app.services.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    ReAct Executor: orchestrates reasoning, parallel tool execution, observation handling,
    and budget enforcement.
    """

    @classmethod
    async def run(
        cls,
        user_query: str,
        plan: AgentPlan,
        budget: AgentBudgetConfig,
        registry: ToolRegistry,
        persona: PersonaConfigDTO,
        conversation_history: List[Dict[str, str]],
        memory_context: str = "",
        excluded_source_ids: Optional[List[str]] = None,
        event_callback: Optional[Callable[[AgentEvent], Any]] = None,
        db: Optional[AsyncSession] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t_start = time.perf_counter()
        excluded_set = set(excluded_source_ids or [])
        collected_sources: List[Dict[str, Any]] = []
        executed_tool_traces: List[Dict[str, Any]] = []

        total_tool_calls_count = 0
        iteration = 0
        draft_answer = ""
        suggest_scholar_escalation = False
        escalation_category = None
        recommended_scholar = None
        recommended_book = None

        # Build initial messages array
        system_instruction = (
            f"نقش تو: {persona.botName or 'دستیار معارفی اتحاد'}\n"
            f"رویکرد فقهی: {persona.fiqhApproach or 'تقریب بین مذاهب و وحدت اسلامی'}\n"
            f"لحن: {persona.tone or 'دوستانه و محترمانه'}\n"
            "دستورالعمل استناد و ارجاع‌دهی:\n"
            "1. در متن پاسخ، هر جا به یکی از منابع استناد می‌کنی، دقیقاً از پیوند مارک‌داون قابل کلیک به صورت [شماره](آدرس) استفاده کن.\n"
            "2. فقط مطالبی را به عنوان حکم یا روایت قطعی بیان کن که در ابزارهای جستجو مستند شده باشند.\n"
            "3. در انتهای پاسخ، بخشی با عنوان «📚 منابع و مراجع:» درج کن و نام منابع را لیست کن.\n"
        )
        if memory_context:
            system_instruction += f"\nپیش‌زمینه و ترجیحات کاربر:\n{memory_context}\n"

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_instruction}
        ]
        # Include recent conversation turns (last 4)
        for h in conversation_history[-4:]:
            messages.append(h)

        # Ensure current query is in messages
        if not messages or messages[-1].get("content") != user_query:
            messages.append({"role": "user", "content": user_query})

        tools_schema = registry.to_openai_tools()

        # Step 0: Execute initial planned tools if provided
        if plan.recommended_tools:
            init_tasks = []
            for item in plan.recommended_tools[:3]:
                t_name = item.get("tool")
                t_args = item.get("arguments", {})
                if t_name and registry.get_tool(t_name):
                    init_tasks.append((t_name, t_args))

            if init_tasks:
                if event_callback:
                    await event_callback(AgentEvent(
                        type=AgentEventType.PLAN.value,
                        data={"plan": plan.to_dict()}
                    ))

                # Execute planned tools in parallel
                exec_tasks = [
                    registry.execute(name=t_name, arguments=t_args, db=db, user_id=user_id, conversation_id=conversation_id)
                    for t_name, t_args in init_tasks
                ]
                results = await asyncio.gather(*exec_tasks, return_exceptions=True)

                for (t_name, t_args), res in zip(init_tasks, results):
                    total_tool_calls_count += 1
                    if isinstance(res, Exception):
                        res_dict = {"success": False, "error": str(res), "data": None, "summary": "خطا در اجرا"}
                    else:
                        res_dict = res

                    executed_tool_traces.append({
                        "tool": t_name,
                        "arguments": t_args,
                        "success": res_dict.get("success", False),
                        "summary": res_dict.get("summary", ""),
                        "latency_ms": res_dict.get("latency_ms", 0.0)
                    })

                    if event_callback:
                        await event_callback(AgentEvent(
                            type=AgentEventType.TOOL_RESULT.value,
                            data={"tool": t_name, "summary": res_dict.get("summary", ""), "data": res_dict.get("data")}
                        ))

                    # Process observations into sources
                    cls._extract_sources_from_tool_data(t_name, res_dict.get("data"), collected_sources, excluded_set)

                    # Inject tool observation into prompt
                    obs_summary = json.dumps(res_dict.get("data", ""), ensure_ascii=False)
                    messages.append({
                        "role": "system",
                        "content": f"[شواهد اولیه از ابزار {t_name}]:\n{obs_summary[:1800]}"
                    })

        # Main ReAct Reasoning Loop
        while iteration < budget.max_tool_iterations:
            elapsed = time.perf_counter() - t_start
            if elapsed >= budget.max_wall_time_seconds or total_tool_calls_count >= budget.max_total_tool_calls:
                logger.info(f"Budget threshold reached (elapsed: {elapsed:.1f}s, tool calls: {total_tool_calls_count}). Generating answer.")
                break

            iteration += 1

            # Call LLM with tools
            llm_res = await LLMProviderService.call_chat_with_tools(
                section_key="agent_executor",
                messages=messages,
                tools=tools_schema,
                tool_choice="auto",
                db=db,
                temperature=0.3,
                user_id=user_id,
                conversation_id=conversation_id
            )

            if not llm_res:
                logger.warning("LLM tools call returned None. Breaking out to synthesis.")
                break

            tool_calls = llm_res.get("tool_calls", [])
            content_text = llm_res.get("text", "")

            # If no tool calls, model gave the draft answer
            if not tool_calls:
                draft_answer = content_text
                break

            # Handle Model-Requested Tool Calls
            tool_execution_coroutines = []
            valid_calls = []

            for tc in tool_calls:
                func_obj = tc.get("function", {})
                name = func_obj.get("name")
                call_id = tc.get("id", f"call_{len(executed_tool_traces)}")
                raw_args = func_obj.get("arguments", "{}")

                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except Exception:
                    args = {}

                if registry.get_tool(name):
                    valid_calls.append((call_id, name, args))
                    if event_callback:
                        await event_callback(AgentEvent(
                            type=AgentEventType.TOOL_CALL.value,
                            data={"tool": name, "arguments": args, "call_id": call_id}
                        ))
                    tool_execution_coroutines.append(
                        registry.execute(name=name, arguments=args, db=db, user_id=user_id, conversation_id=conversation_id)
                    )

            if not tool_execution_coroutines:
                draft_answer = content_text
                break

            # Execute model-requested tools in parallel
            results = await asyncio.gather(*tool_execution_coroutines, return_exceptions=True)

            # Record assistant call in history
            messages.append({
                "role": "assistant",
                "content": content_text or None,
                "tool_calls": tool_calls
            })

            # Append tool outputs as tool roles
            for (call_id, name, args), res in zip(valid_calls, results):
                total_tool_calls_count += 1
                if isinstance(res, Exception):
                    res_dict = {"success": False, "error": str(res), "data": None, "summary": "خطا"}
                else:
                    res_dict = res

                if name == "escalate_to_scholar":
                    suggest_scholar_escalation = True
                    escalation_category = args.get("category", "احکام شرعی و فقهی")

                if name == "recommend_scholar_and_book" and isinstance(res_dict.get("data"), dict):
                    recommended_scholar = res_dict["data"].get("scholar")
                    recommended_book = res_dict["data"].get("book")

                executed_tool_traces.append({
                    "tool": name,
                    "arguments": args,
                    "success": res_dict.get("success", False),
                    "summary": res_dict.get("summary", ""),
                    "latency_ms": res_dict.get("latency_ms", 0.0)
                })

                if event_callback:
                    await event_callback(AgentEvent(
                        type=AgentEventType.TOOL_RESULT.value,
                        data={"tool": name, "summary": res_dict.get("summary", ""), "data": res_dict.get("data")}
                    ))

                cls._extract_sources_from_tool_data(name, res_dict.get("data"), collected_sources, excluded_set)

                # Append tool observation
                obs_content = json.dumps(res_dict.get("data", ""), ensure_ascii=False)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": obs_content[:2000]
                })

        # Final Synthesis step if draft_answer is still empty
        if not draft_answer:
            synthesis_prompt = (
                "بر اساس تمامی شواهد، مستندات و بررسی‌های انجام‌شده فوق، پاسخ جامع، مستند و دقیقی به پرسش کاربر بنویس.\n"
                "تمامی استنادها را با پیوند مارک‌داون [شماره](آدرس) مشخص کن و در انتها فهرست مراجع را بیاور."
            )
            messages.append({"role": "user", "content": synthesis_prompt})
            synth_res = await LLMProviderService.call_chat_with_tools(
                section_key="agent_executor",
                messages=messages,
                tools=None,
                db=db,
                temperature=0.3,
                user_id=user_id,
                conversation_id=conversation_id
            )
            draft_answer = synth_res.get("text", "") if synth_res else ""

        # Build Citations list DTOs
        citations, context_prompt = cls._build_citations_list(collected_sources)

        total_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

        return {
            "draftAnswer": draft_answer,
            "sources": citations,
            "rawSources": collected_sources,
            "contextPrompt": context_prompt,
            "toolTraces": executed_tool_traces,
            "totalToolCalls": total_tool_calls_count,
            "iterations": iteration,
            "totalLatencyMs": total_latency_ms,
            "suggestScholarEscalation": suggest_scholar_escalation,
            "escalationCategory": escalation_category,
            "recommendedScholar": recommended_scholar,
            "recommendedBook": recommended_book
        }

    @classmethod
    def _extract_sources_from_tool_data(
        cls,
        tool_name: str,
        data: Any,
        sources_list: List[Dict[str, Any]],
        excluded_set: set
    ):
        if not data:
            return

        if tool_name == "search_library" and isinstance(data, list):
            for item in data:
                cid = item.get("chunkId") or item.get("id")
                if cid and cid not in excluded_set and not any(s.get("id") == cid for s in sources_list):
                    sources_list.append({
                        "id": cid,
                        "type": "BOOK",
                        "title": f"{item.get('bookTitle', 'کتاب اسلامی')} - {item.get('chapterTitle', '')}".strip(" -"),
                        "targetUrl": f"source://book/{item.get('bookTitle', 'bk')}/chunk/{cid}",
                        "excerpt": item.get("excerpt", "")[:300],
                        "madhhab": item.get("madhhab"),
                        "pageNumber": item.get("pageNumber"),
                        "score": item.get("score")
                    })
        elif tool_name == "search_quran" and isinstance(data, list):
            for a in data:
                aid = a.get("id") or f"ayah_{a.get('surahId')}_{a.get('ayahNumber')}"
                if aid not in excluded_set and not any(s.get("id") == aid for s in sources_list):
                    sources_list.append({
                        "id": aid,
                        "type": "QURAN",
                        "title": f"قرآن کریم، سوره {a.get('surahId')}، آیه {a.get('ayahNumber')}",
                        "targetUrl": f"source://quran/surah/{a.get('surahId')}/ayah/{a.get('ayahNumber')}",
                        "excerpt": f"«{a.get('textArabic', '')}» - ترجمه: {a.get('textPersian', '')}",
                        "pageNumber": a.get("pageNumber"),
                        "score": 10.0
                    })
        elif tool_name == "search_consultations" and isinstance(data, list):
            for t in data:
                tid = t.get("threadId")
                if tid and tid not in excluded_set and not any(s.get("id") == tid for s in sources_list):
                    sources_list.append({
                        "id": tid,
                        "type": "CONSULTATION",
                        "title": f"استفتاء: {t.get('title', '')}",
                        "targetUrl": f"source://consultation/thread/{tid}",
                        "excerpt": t.get("excerpt", "")[:250],
                        "madhhab": None
                    })
        elif tool_name == "compare_madhhabs" and isinstance(data, dict):
            findings = data.get("schoolFindings", {})
            for m_name, items in findings.items():
                for it in items:
                    t_title = f"{m_name} ({it.get('bookTitle', '')})"
                    if not any(s.get("title") == t_title for s in sources_list):
                        sources_list.append({
                            "id": f"comp_{m_name}_{len(sources_list)}",
                            "type": "BOOK",
                            "title": t_title,
                            "targetUrl": f"source://fiqh/comparative/{m_name}",
                            "excerpt": it.get("excerpt", "")[:250],
                            "madhhab": m_name,
                            "pageNumber": it.get("pageNumber")
                        })

    @classmethod
    def _build_citations_list(
        cls,
        collected_sources: List[Dict[str, Any]]
    ) -> Tuple[List[SourceCitationDTO], str]:
        citations = []
        prompt_lines = []

        for idx, item in enumerate(collected_sources[:6], start=1):
            target_url = item.get("targetUrl") or f"source://item/{idx}"
            dto = SourceCitationDTO(
                index=idx,
                type=item.get("type", "BOOK"),
                title=item.get("title", f"منبع {idx}"),
                targetUrl=target_url,
                excerpt=item.get("excerpt"),
                madhhab=item.get("madhhab"),
                pageNumber=item.get("pageNumber"),
                score=item.get("score"),
                language="fa"
            )
            citations.append(dto)
            prompt_lines.append(
                f"[{idx}] منبع: {dto.title}\n"
                f"پیوند کلیک: {dto.targetUrl}\n"
                f"شواهد: {dto.excerpt}\n"
            )

        context_prompt = "\n---\n".join(prompt_lines) if prompt_lines else "بدون استناد مستقیم."
        return citations, context_prompt
