import re
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.ai_chat import PersonaConfigDTO
from app.services.llm_provider_service import LLMProviderService

logger = logging.getLogger(__name__)


def normalize_madhhab(madhhab: Optional[str]) -> Optional[str]:
    if not madhhab:
        return None
    m = str(madhhab).strip().lower()
    if any(k in m for k in ["shafi", "شافع"]):
        return "شافعی"
    if any(k in m for k in ["hanafi", "حنف"]):
        return "حنفی"
    if any(k in m for k in ["jafari", "shia", "جعفر", "شیع"]):
        return "جعفری"
    if any(k in m for k in ["maliki", "مالک"]):
        return "مالکی"
    if any(k in m for k in ["hanbali", "حنبل"]):
        return "حنبلی"
    return madhhab


@dataclass
class AgentPlan:
    is_direct_answer: bool = False
    requires_citations: bool = False
    clarification_needed: Optional[str] = None
    target_madhhab: Optional[str] = None
    sub_questions: List[str] = field(default_factory=list)
    recommended_tools: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_summary: str = ""

    @property
    def requires_tools(self) -> bool:
        return bool(self.recommended_tools) or self.requires_citations

    @property
    def selected_tools(self) -> List[str]:
        return [t.get("tool") for t in self.recommended_tools if isinstance(t, dict) and t.get("tool")]

    @property
    def madhhab(self) -> Optional[str]:
        return normalize_madhhab(self.target_madhhab)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_direct_answer": self.is_direct_answer,
            "requires_citations": self.requires_citations,
            "clarification_needed": self.clarification_needed,
            "target_madhhab": self.target_madhhab,
            "sub_questions": self.sub_questions,
            "recommended_tools": self.recommended_tools,
            "reasoning_summary": self.reasoning_summary
        }


class AgentPlanner:
    """
    Cognitive Planner: extracts intent, resolves madhhab, decomposes complex religious/fiqh
    inquiries into structured sub-steps, and determines whether tools are mandatory.
    """

    @classmethod
    async def create_plan(
        cls,
        user_query: str,
        persona: PersonaConfigDTO,
        conversation_history: List[Dict[str, str]],
        memory_context: str = "",
        available_tool_names: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None
    ) -> AgentPlan:
        # Check if question requires legal rulings or citations
        q_clean = user_query.strip().lower()
        ruling_keywords = [
            "حکم", "نجس", "طهارت", "حلال", "حرام", "نماز", "فقه", "روزه",
            "خمس", "وضو", "غسل", "شرط", "باطل", "آیه", "سوره", "حدیث", "روایت"
        ]
        is_fiqh_query = any(k in q_clean for k in ruling_keywords)

        # Fast heuristic check for pure conversational greetings
        simple_greetings = ["سلام", "سلام علیکم", "درود", "خوبی", "تشکر", "ممنون", "خداحافظ", "یا علی", "خدا قوت"]
        if (any(g in q_clean for g in simple_greetings) or q_clean in simple_greetings) and not is_fiqh_query and len(q_clean) < 45:
            return AgentPlan(
                is_direct_answer=True,
                requires_citations=False,
                reasoning_summary="احوال‌پرسی یا تعارفات عمومی؛ پاسخ مستقیم بدون نیاز به ابزار."
            )

        # Madhhab Resolution Hierarchy:
        # 1. Explicit in query
        target_madhhab = None
        if "شافع" in q_clean:
            target_madhhab = "شافعی"
        elif "حنف" in q_clean:
            target_madhhab = "حنفی"
        elif "جعفر" in q_clean:
            target_madhhab = "جعفری"
        elif "شیع" in q_clean:
            target_madhhab = "جعفری"
        elif "مالک" in q_clean:
            target_madhhab = "مالکی"
        elif "حنبل" in q_clean:
            target_madhhab = "حنبلی"

        # 2. Persona configuration
        if not target_madhhab and persona and persona.fiqhApproach:
            fa = persona.fiqhApproach
            if fa in ("SHAFII", "شافعی"):
                target_madhhab = "شافعی"
            elif fa in ("HANAFI", "حنفی"):
                target_madhhab = "حنفی"
            elif fa in ("JAFARI", "SHIA", "شیعه"):
                target_madhhab = "جعفری"

        # 3. Memory context lookup
        if not target_madhhab and memory_context:
            for m in ["شافعی", "حنفی", "جعفری", "شیعه اثناعشری", "مالکی", "حنبلی"]:
                if m in memory_context:
                    target_madhhab = "جعفری" if "شیعه" in m else m
                    break

        system_prompt = (
            "You are an advanced cognitive Research & Knowledge Planner for a comprehensive multi-source retrieval system.\n"
            "Your objective is to analyze the user query and formulate a rigorous, structured research plan.\n"
            "\n"
            "UNIVERSAL DECOMPOSITION RULES FOR `sub_questions`:\n"
            "1. NEVER repeat the user query verbatim.\n"
            "2. Decompose any complex query into 2 to 4 distinct, complementary, and mutually exclusive sub-questions:\n"
            "   - Layer 1 (Conceptual & Definitional): Clarifies core definitions, essential principles, or foundational premises.\n"
            "   - Layer 2 (Mechanisms, Conditions & Evidence): Investigates criteria, operational rules, textual or empirical proofs, and conditions.\n"
            "   - Layer 3 (Applications, Perspectives & Edge Cases): Explores practical implementations, comparative viewpoints (across schools or traditions if applicable), exceptions, or contemporary relevance.\n"
            "3. Multilingual Adaptability: Formulate sub-questions matching the primary inquiry language (Persian, Arabic, or English) with technical precision.\n"
            "\n"
            "PLANNING & CITATIONS POLICY:\n"
            "- If the query involves authoritative citations, textual evidence, doctrinal rulings, or literature lookups: set `requires_citations = true` and `is_direct_answer = false`.\n"
            "- If the query is a simple greeting or trivial conversational remark: set `is_direct_answer = true`.\n"
            "- If the query requires comparative analysis across multiple schools/perspectives without a specific target school: select comparative retrieval tools.\n"
            "\n"
            "OUTPUT FORMAT: Return STRICTLY a valid JSON object matching this schema (no commentary):\n"
            "{\n"
            '  "is_direct_answer": false,\n'
            '  "requires_citations": true,\n'
            '  "clarification_needed": null,\n'
            '  "target_madhhab": null,\n'
            '  "sub_questions": [\n'
            '    "<sub_question_1_foundational_concepts>",\n'
            '    "<sub_question_2_mechanisms_and_evidence>",\n'
            '    "<sub_question_3_applications_or_perspectives>"\n'
            '  ],\n'
            '  "recommended_tools": [\n'
            '    {"tool": "<tool_name>", "arguments": {"query": "<targeted_search_query>"}}\n'
            '  ],\n'
            '  "reasoning_summary": "<concise_summary_of_planned_strategy>"\n'
            "}"
        )

        user_content = (
            f"User Query: {user_query}\n"
            f"Target School/Madhhab: {target_madhhab or 'Not specified (use comparative cross-school approach if needed)'}\n"
            f"User Memory Context:\n{memory_context or 'None'}\n"
            f"Available Tools: {', '.join(available_tool_names or ['search_library', 'read_chunk', 'search_quran', 'compare_madhhabs', 'search_consultations', 'escalate_to_scholar'])}"
        )

        try:
            resp = await LLMProviderService.call_chat(
                prompt=user_content,
                system_instruction=system_prompt,
                section_key="agent_planner",
                db=db,
                temperature=0.2,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            raw_text = ""
            if isinstance(resp, dict):
                raw_text = str(resp.get("text") or "").strip()
            elif isinstance(resp, str):
                raw_text = resp.strip()

            if raw_text:
                if "<think>" in raw_text:
                    if "</think>" in raw_text:
                        raw_text = raw_text.split("</think>")[-1].strip()
                    else:
                        raw_text = raw_text.split("<think>")[-1].strip()

                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()

                parsed = None
                try:
                    parsed = json.loads(raw_text)
                except Exception:
                    m = re.search(r"\{[\s\S]*\}", raw_text)
                    if m:
                        try:
                            parsed = json.loads(m.group(0))
                        except Exception:
                            pass

                if parsed and isinstance(parsed, dict):
                    raw_sub_qs = parsed.get("sub_questions", [])
                    clean_sub_qs = [
                        str(sq).strip() for sq in raw_sub_qs
                        if str(sq).strip() and str(sq).strip() != user_query.strip() and not str(sq).startswith("<")
                    ]
                    if not clean_sub_qs:
                        clean_sub_qs = [
                            f"مبانی، تعاریف و ابعاد مفهومی پیرامون «{user_query[:40]}»",
                            f"احکام، قواعد، شروط یا ادله مرتبط با «{user_query[:40]}»",
                            f"کاربردها، مصادیق و دیدگاه‌های تکمیلی/تطبیقی در خصوص «{user_query[:40]}»"
                        ]

                    return AgentPlan(
                        is_direct_answer=bool(parsed.get("is_direct_answer", False)),
                        requires_citations=bool(parsed.get("requires_citations", is_fiqh_query)),
                        clarification_needed=parsed.get("clarification_needed"),
                        target_madhhab=normalize_madhhab(parsed.get("target_madhhab")) or target_madhhab,
                        sub_questions=clean_sub_qs,
                        recommended_tools=parsed.get("recommended_tools", []),
                        reasoning_summary=parsed.get("reasoning_summary", "")
                    )
        except Exception as e:
            logger.warning(f"AgentPlanner LLM call failed: {e}. Falling back to rule-based plan.")

        # Fallback rule-based plan
        default_tools = []
        if is_fiqh_query:
            if target_madhhab:
                default_tools.append({
                    "tool": "search_library",
                    "arguments": {"query": user_query, "madhhab": target_madhhab}
                })
            else:
                default_tools.append({
                    "tool": "compare_madhhabs",
                    "arguments": {"topic": user_query}
                })
        else:
            default_tools.append({
                "tool": "search_library",
                "arguments": {"query": user_query}
            })

        fallback_sub_questions = [
            f"مبانی، تعاریف و مفاهیم اصلی پیرامون «{user_query[:40]}»",
            f"شروط، قواعد و ادله مرتبط با «{user_query[:40]}»",
            f"کاربردها، مصادیق و دیدگاه‌های تکمیلی در خصوص «{user_query[:40]}»"
        ]

        return AgentPlan(
            is_direct_answer=not is_fiqh_query and len(q_clean) < 20,
            requires_citations=is_fiqh_query,
            target_madhhab=target_madhhab,
            sub_questions=fallback_sub_questions,
            recommended_tools=default_tools,
            reasoning_summary="طرح‌ریزی شناختی ساختاریافته بر پایه رویکرد سه‌لایه."
        )
