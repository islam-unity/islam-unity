from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class AgentBudgetConfig:
    max_tool_iterations: int = 5
    max_total_tool_calls: int = 8
    max_wall_time_seconds: float = 40.0
    allow_revision: bool = True
    max_revisions: int = 1
    min_relevance_score: float = 6.0


class BudgetManager:
    """
    Manages dynamic budgets for the Agent lifecycle based on persona detailLevel,
    query depth cues, and administrative section extra_params.
    """

    @classmethod
    def resolve_budget(
        cls,
        detail_level: Optional[str] = "STANDARD",
        user_query: Optional[str] = "",
        extra_params: Optional[Dict[str, Any]] = None
    ) -> AgentBudgetConfig:
        params = extra_params or {}

        # 1. Base profile according to detail_level
        dl = (detail_level or "STANDARD").upper()
        if dl in ("BRIEF", "SHORT", "QUICK"):
            base_iterations = 3
            base_tool_calls = 4
            base_timeout = 25.0
            allow_rev = False
        elif dl in ("DETAILED", "IN_DEPTH"):
            base_iterations = 6
            base_tool_calls = 9
            base_timeout = 45.0
            allow_rev = True
        elif dl in ("COMPREHENSIVE", "RESEARCH", "SCHOLARLY"):
            base_iterations = 8
            base_tool_calls = 12
            base_timeout = 55.0
            allow_rev = True
        else:  # STANDARD / BALANCED
            base_iterations = 5
            base_tool_calls = 7
            base_timeout = 38.0
            allow_rev = True

        # 2. Dynamic query keyword adjustment
        q_lower = (user_query or "").lower()
        comprehensive_keywords = [
            "جامع", "پژوهشی", "تفصیلی", "کامل", "تمام اقوال", "همه مذاهب",
            "بررسی دقیق", "با جزییات", "مقایسه کامل"
        ]
        if any(kw in q_lower for kw in comprehensive_keywords):
            base_iterations = max(base_iterations, 7)
            base_tool_calls = max(base_tool_calls, 10)
            base_timeout = max(base_timeout, 50.0)

        # 3. Apply administrative overrides from section extra_params if configured
        final_iterations = int(params.get("max_tool_iterations", base_iterations))
        final_tool_calls = int(params.get("max_total_tool_calls", base_tool_calls))
        final_timeout = float(params.get("timeout_seconds", base_timeout))
        final_allow_rev = bool(params.get("allow_revision", allow_rev))
        final_max_rev = int(params.get("max_revisions", 1 if final_allow_rev else 0))

        return AgentBudgetConfig(
            max_tool_iterations=final_iterations,
            max_total_tool_calls=final_tool_calls,
            max_wall_time_seconds=final_timeout,
            allow_revision=final_allow_rev,
            max_revisions=final_max_rev,
            min_relevance_score=float(params.get("min_relevance_score", 5.5))
        )
