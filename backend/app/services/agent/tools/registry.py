import time
import inspect
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable, List, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    func: Callable[..., Awaitable[Any]]
    summarizer: Optional[Callable[[Dict[str, Any], Any], str]] = None


class ToolRegistry:
    """
    Modular Tool Registry for the Agent Engine.
    Exposes OpenAI-compatible function calling schemas and manages safe asynchronous execution.
    """

    def __init__(self, name: str = "default"):
        self.name = name
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool_spec: ToolSpec) -> "ToolRegistry":
        self._tools[tool_spec.name] = tool_spec
        return self

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def list_names(self) -> List[str]:
        return list(self._tools.keys())

    def to_openai_tools(self, filter_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Converts registered tools into OpenAI tools array format.
        """
        tools_list = []
        for name, spec in self._tools.items():
            if filter_names is not None and name not in filter_names:
                continue
            tools_list.append({
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters
                }
            })
        return tools_list

    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        **context
    ) -> Dict[str, Any]:
        """
        Executes a registered tool with timing, error capture, and summary extraction.
        """
        spec = self._tools.get(name)
        if not spec:
            return {
                "success": False,
                "error": f"ابزار '{name}' یافت نشد.",
                "data": None,
                "summary": f"ابزار '{name}' نامعتبر است",
                "latency_ms": 0.0
            }

        t_start = time.perf_counter()
        try:
            # Inspect tool function signature to inject supported context arguments (db, user_id, etc.)
            sig = inspect.signature(spec.func)
            call_kwargs = dict(arguments)
            for ctx_key, ctx_val in context.items():
                if ctx_key in sig.parameters and ctx_key not in call_kwargs:
                    call_kwargs[ctx_key] = ctx_val

            result = await spec.func(**call_kwargs)
            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

            summary = ""
            if spec.summarizer:
                try:
                    summary = spec.summarizer(arguments, result)
                except Exception as sum_err:
                    logger.debug(f"Error in tool summarizer: {sum_err}")
            if not summary:
                if isinstance(result, list):
                    summary = f"{len(result)} مورد یافت شد"
                elif isinstance(result, dict) and "count" in result:
                    summary = f"{result['count']} مورد یافت شد"
                else:
                    summary = "عملیات با موفقیت انجام شد"

            return {
                "success": True,
                "data": result,
                "summary": summary,
                "latency_ms": latency_ms,
                "error": None
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
            err_msg = str(e) or type(e).__name__
            logger.warning(f"Error executing tool '{name}': {err_msg}")
            return {
                "success": False,
                "data": None,
                "summary": f"خطا در اجرای ابزار: {err_msg[:60]}",
                "latency_ms": latency_ms,
                "error": err_msg
            }
