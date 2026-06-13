"""
MCP Server — FastAPI router for the Model Context Protocol endpoint.

Mounted at /mcp/v1 in app/main.py.

Endpoints:
  GET  /mcp/v1/tools        — list available MCP tools
  POST /mcp/v1/tools/call   — call a tool with parameters
  GET  /mcp/v1/health       — server health check

The synthesize_answer tool invokes the full DocSearch pipeline
(intent classification → specialist agent → reasoning → synthesis).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.intent_classifier import classify_intent, _regex_classify
from app.agents.orchestrator import research_agent
from app.agents.state import AgentState
from app.api.deps import get_current_user
from app.db.session import get_db
from app.mcp.schemas import MCPToolCallRequest, MCPToolCallResponse, MCPToolsListResponse
from app.mcp.tools import MCP_TOOLS, MCP_TOOL_MAP
from app.models.user import User
from app.schemas.comparison import ComparisonRequest
from app.schemas.search import SearchRequest
from app.services.comparison_service import ComparisonService
from app.services.retrieval_service import retrieval_service


mcp_router = APIRouter()


@mcp_router.get("/health")
async def mcp_health():
    return {
        "status": "ok",
        "server": "docsearch-mcp",
        "version": "1.0.0",
        "protocol": "mcp/1.0",
        "tools": len(MCP_TOOLS),
    }


@mcp_router.get("/tools", response_model=MCPToolsListResponse)
async def list_tools():
    """List all available MCP tools with their schemas."""
    return MCPToolsListResponse(tools=MCP_TOOLS)


@mcp_router.post("/tools/call", response_model=MCPToolCallResponse)
async def call_tool(
    request: MCPToolCallRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Invoke an MCP tool with the provided parameters."""
    start_ms = time.perf_counter()

    if request.tool not in MCP_TOOL_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown tool '{request.tool}'. Available tools: {list(MCP_TOOL_MAP.keys())}",
        )

    try:
        result = await _dispatch(request.tool, request.parameters, user, db)
        duration = int((time.perf_counter() - start_ms) * 1000)
        return MCPToolCallResponse(tool=request.tool, result=result, duration_ms=duration)
    except Exception as exc:
        duration = int((time.perf_counter() - start_ms) * 1000)
        return MCPToolCallResponse(
            tool=request.tool,
            result=None,
            error=str(exc),
            duration_ms=duration,
        )


async def _dispatch(tool: str, params: dict, user: User, db: Session):
    """Route tool call to implementation."""

    if tool == "search_workspace":
        workspace_id = params["workspace_id"]
        query = params["query"]
        top_k = int(params.get("top_k", 5))
        retrieval_service.ensure_workspace_index(workspace_id, db)
        contexts, citations = retrieval_service.search(workspace_id, query, top_k=top_k)
        return {
            "passages": contexts,
            "citations": [
                {
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "chunk_reference": c.chunk_reference,
                    "source_type": c.source_type,
                }
                for c in citations
            ],
        }

    if tool == "classify_intent":
        query = params["query"]
        # Build a minimal state and run classifier
        state = AgentState(query=query, workspace_id="mcp")
        state = classify_intent(state)
        return {
            "intent": state.intent,
            "task_type": state.task_type,
            "sub_queries": state.sub_queries,
            "confidence": state.confidence,
        }

    if tool == "synthesize_answer":
        payload = SearchRequest(
            workspace_id=params["workspace_id"],
            query=params["query"],
            include_web=bool(params.get("include_web", True)),
            top_k=int(params.get("top_k", 5)),
        )
        result = research_agent.run(payload, user, db)
        return {
            "answer": result.answer,
            "intent": result.intent,
            "task_type": result.task_type,
            "confidence": result.confidence,
            "reasoning_chain": [r.model_dump() for r in result.reasoning_chain],
            "evidence_gaps": result.evidence_gaps,
            "citations": [c.model_dump() for c in result.citations],
        }

    if tool == "compare_documents":
        req = ComparisonRequest(
            workspace_id=params["workspace_id"],
            left_document_id=params["left_document_id"],
            right_document_id=params["right_document_id"],
        )
        result = ComparisonService().compare_documents(req, user=user, db=db)
        return {
            "summary": result.summary,
            "added_sections": result.added_sections,
            "removed_sections": result.removed_sections,
            "modified_sections": result.modified_sections,
        }

    raise ValueError(f"Tool '{tool}' has no implementation")
