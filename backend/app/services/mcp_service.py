"""
MCP Connector Registry.

Returns the status of all MCP connectors and built-in tools.
Built-in tools (search_workspace, classify_intent, etc.) are now active.
External connectors (GitHub, Notion, etc.) remain planned.
"""
from app.schemas.mcp import MCPConnectorResponse


def list_connectors() -> list[MCPConnectorResponse]:
    """List all MCP connectors — built-in tools are active, external connectors planned."""
    return [
        # ── Built-in active tools ───────────────────────────────────
        MCPConnectorResponse(
            name="search_workspace",
            status="active",
            capabilities=["semantic_search", "hybrid_retrieval", "intent_aware_ranking"],
            auth_strategy="jwt",
        ),
        MCPConnectorResponse(
            name="classify_intent",
            status="active",
            capabilities=["intent_classification", "sub_query_decomposition", "confidence_scoring"],
            auth_strategy="jwt",
        ),
        MCPConnectorResponse(
            name="synthesize_answer",
            status="active",
            capabilities=["chain_of_thought", "multi_hop_retrieval", "evidence_gap_detection", "cited_answers"],
            auth_strategy="jwt",
        ),
        MCPConnectorResponse(
            name="compare_documents",
            status="active",
            capabilities=["structured_diff", "section_comparison", "similarity_analysis"],
            auth_strategy="jwt",
        ),
        # ── Planned external connectors ─────────────────────────────
        MCPConnectorResponse(
            name="github",
            status="planned",
            capabilities=["repo_search", "issues", "pull_requests", "code_context"],
            auth_strategy="oauth_app",
        ),
        MCPConnectorResponse(
            name="google_drive",
            status="planned",
            capabilities=["file_search", "folder_sync", "document_ingestion"],
            auth_strategy="oauth2",
        ),
        MCPConnectorResponse(
            name="notion",
            status="planned",
            capabilities=["page_search", "knowledge_sync", "workspace_docs"],
            auth_strategy="oauth2",
        ),
        MCPConnectorResponse(
            name="slack",
            status="planned",
            capabilities=["message_search", "channel_ingestion", "thread_context"],
            auth_strategy="oauth2",
        ),
        MCPConnectorResponse(
            name="confluence",
            status="planned",
            capabilities=["page_search", "space_ingestion", "wiki_sync"],
            auth_strategy="oauth2",
        ),
    ]
