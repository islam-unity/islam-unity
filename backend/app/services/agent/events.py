import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, Optional, List


class AgentEventType(str, Enum):
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    VERIFY = "verify"
    TOKEN = "token"
    SOURCES = "sources"
    STATUS = "status"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentEvent:
    type: str
    stage: Optional[str] = None
    message: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        res = {"type": self.type}
        if self.stage:
            res["stage"] = self.stage
        if self.message:
            res["message"] = self.message
        if self.data:
            res.update(self.data)
        return res

    def to_sse_line(self) -> str:
        payload = self.to_dict()
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def to_legacy_status(self) -> Optional[Dict[str, Any]]:
        """
        Maps structured agent events into legacy status events for backward compatibility
        with older mobile app builds.
        """
        if self.type == AgentEventType.PLAN.value:
            plan_data = self.data.get("plan", {})
            sub_q = plan_data.get("sub_questions", [])
            q_info = f" ({len(sub_q)} گام بررسی)" if sub_q else ""
            return {
                "type": "status",
                "stage": "PLANNING",
                "message": f"📋 تدوین نقشه استدلال و بررسی مسئله{q_info}..."
            }
        elif self.type == AgentEventType.TOOL_CALL.value:
            tool_name = self.data.get("tool", "")
            tool_fa = {
                "search_library": "جستجوی تخصصی در کتب و فصول کتابخانه",
                "read_chunk": "مطالعه متن کامل و شواهد فصل",
                "browse_book_toc": "بررسی فهرست ابواب و فصول کتاب",
                "search_quran": "جستجو و استخراج آیات و ترجمه",
                "search_consultations": "بررسی استفتائات و پاسخ‌های مشاوران",
                "compare_madhhabs": "مقایسه تطبیقی آرای مذاهب اسلامی",
                "escalate_to_scholar": "آماده‌سازی پیش‌نویس ارجاع به عالم دینی"
            }.get(tool_name, tool_name)
            return {
                "type": "status",
                "stage": "SEARCHING",
                "message": f"🔍 اجرای ابزار: {tool_fa}..."
            }
        elif self.type == AgentEventType.TOOL_RESULT.value:
            summary = self.data.get("summary") or "دریافت شواهد"
            return {
                "type": "status",
                "stage": "PROCESSING",
                "message": f"📑 {summary}"
            }
        elif self.type == AgentEventType.VERIFY.value:
            verdict = self.data.get("verdict", "PASSED")
            verdict_msg = "تطابق احکام با منابع احراز شد" if verdict == "PASSED" else "اصلاح و اعتبارسنجی ارجاعات"
            return {
                "type": "status",
                "stage": "EVALUATING",
                "message": f"⚖️ اعتبارسنجی احکام و نظرات: {verdict_msg}..."
            }
        elif self.type == AgentEventType.STATUS.value:
            return {
                "type": "status",
                "stage": self.stage or "INFO",
                "message": self.message or ""
            }
        return None
