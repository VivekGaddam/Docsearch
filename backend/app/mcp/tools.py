"""
MCP Tool Definitions.

Defines the four core MCP tools that expose DocSearch capabilities
to external MCP clients (e.g. Claude Desktop, LLM agents).

Tools:
  search_workspace    — semantic search over workspace docs + reasoning
  classify_intent     — classify query intent and decompose sub-queries
  synthesize_answer   — full pipeline: search → reason → synthesize
  compare_documents   — structured document comparison
"""
from __future__ import annotations

from app.mcp.schemas import MCPTool, MCPToolParameter


MCP_TOOLS: list[MCPTool] = [
    MCPTool(
        name="search_workspace",
        description=(
            "Semantically search documents in a workspace and return relevant passages "
            "with citations. Supports hybrid sparse+dense retrieval with intent-aware re-ranking."
        ),
        parameters={
            "workspace_id": MCPToolParameter(type="string", description="The workspace UUID to search"),
            "query": MCPToolParameter(type="string", description="The search query"),
            "top_k": MCPToolParameter(type="integer", description="Number of results to return (default: 5)", required=False),
        },
        returns="List of relevant passages with document citations",
    ),
    MCPTool(
        name="classify_intent",
        description=(
            "Classify the intent of a query using the LLM-based intent classifier. "
            "Returns intent type (summarize|compare|extract|research|explain|qa|general), "
            "sub-queries, and confidence score."
        ),
        parameters={
            "query": MCPToolParameter(type="string", description="The query to classify"),
        },
        returns="Intent classification with task_type, sub_queries, confidence, and reasoning",
    ),
    MCPTool(
        name="synthesize_answer",
        description=(
            "Run the full DocSearch pipeline: intent classification → specialist agent retrieval "
            "→ chain-of-thought reasoning → synthesized answer. Returns a human-quality, "
            "cited answer with reasoning chain and evidence gaps."
        ),
        parameters={
            "workspace_id": MCPToolParameter(type="string", description="The workspace UUID"),
            "query": MCPToolParameter(type="string", description="The question to answer"),
            "include_web": MCPToolParameter(type="boolean", description="Include web search results (default: true)", required=False),
            "top_k": MCPToolParameter(type="integer", description="Number of chunks to retrieve (default: 5)", required=False),
        },
        returns="Synthesized answer with citations, reasoning chain, evidence gaps, and intent metadata",
    ),
    MCPTool(
        name="compare_documents",
        description=(
            "Compare two documents in a workspace and return a structured analysis "
            "of similarities, differences, added/removed/modified sections."
        ),
        parameters={
            "workspace_id": MCPToolParameter(type="string", description="The workspace UUID"),
            "left_document_id": MCPToolParameter(type="string", description="ID of the first document"),
            "right_document_id": MCPToolParameter(type="string", description="ID of the second document"),
        },
        returns="Structured comparison with summary, added, removed, and modified sections",
    ),
]

MCP_TOOL_MAP = {tool.name: tool for tool in MCP_TOOLS}
