"""MCP (Model Context Protocol) request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MCPToolParameter(BaseModel):
    type: str
    description: str
    required: bool = True


class MCPTool(BaseModel):
    name: str
    description: str
    parameters: dict[str, MCPToolParameter]
    returns: str


class MCPToolsListResponse(BaseModel):
    tools: list[MCPTool]
    server_name: str = "docsearch-mcp"
    version: str = "1.0.0"
    protocol: str = "mcp/1.0"


class MCPToolCallRequest(BaseModel):
    tool: str
    parameters: dict[str, Any]


class MCPToolCallResponse(BaseModel):
    tool: str
    result: Any
    error: str | None = None
    duration_ms: int | None = None
