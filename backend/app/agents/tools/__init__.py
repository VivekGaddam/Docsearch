from app.agents.tools.comparison import document_comparison_tool
from app.agents.tools.synthesizer import synthesizer_tool
from app.agents.tools.web_search import web_search_tool
from app.agents.tools.workspace_search import workspace_search_tool

TOOL_REGISTRY = {
    "workspace_search": workspace_search_tool,
    "web_search": web_search_tool,
    "document_comparison": document_comparison_tool,
    "synthesizer": synthesizer_tool,
}

__all__ = [
    "TOOL_REGISTRY",
    "workspace_search_tool",
    "web_search_tool",
    "document_comparison_tool",
    "synthesizer_tool",
]
