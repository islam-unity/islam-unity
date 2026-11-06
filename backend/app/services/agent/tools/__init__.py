from app.services.agent.tools.registry import ToolRegistry, ToolSpec
from app.services.agent.tools.library_tools import (
    SEARCH_LIBRARY_TOOL, READ_CHUNK_TOOL, BROWSE_BOOK_TOC_TOOL
)
from app.services.agent.tools.quran_tools import SEARCH_QURAN_TOOL
from app.services.agent.tools.consultation_tools import (
    SEARCH_CONSULTATIONS_TOOL, ESCALATE_TO_SCHOLAR_TOOL, RECOMMEND_SCHOLAR_AND_BOOK_TOOL
)
from app.services.agent.tools.fiqh_tools import COMPARE_MADHHABS_TOOL


def get_default_chat_tools_registry() -> ToolRegistry:
    """
    Creates and returns the pre-configured tool registry for the main Islamic AI Chat Agent.
    """
    registry = ToolRegistry(name="chat_agent_registry")
    registry.register(SEARCH_LIBRARY_TOOL)
    registry.register(READ_CHUNK_TOOL)
    registry.register(BROWSE_BOOK_TOC_TOOL)
    registry.register(SEARCH_QURAN_TOOL)
    registry.register(SEARCH_CONSULTATIONS_TOOL)
    registry.register(COMPARE_MADHHABS_TOOL)
    registry.register(ESCALATE_TO_SCHOLAR_TOOL)
    registry.register(RECOMMEND_SCHOLAR_AND_BOOK_TOOL)
    return registry


__all__ = [
    "ToolRegistry",
    "ToolSpec",
    "get_default_chat_tools_registry",
    "SEARCH_LIBRARY_TOOL",
    "READ_CHUNK_TOOL",
    "BROWSE_BOOK_TOC_TOOL",
    "SEARCH_QURAN_TOOL",
    "SEARCH_CONSULTATIONS_TOOL",
    "COMPARE_MADHHABS_TOOL",
    "ESCALATE_TO_SCHOLAR_TOOL",
    "RECOMMEND_SCHOLAR_AND_BOOK_TOOL"
]
