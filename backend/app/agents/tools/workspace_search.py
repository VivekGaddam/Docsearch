from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.planner import is_overview_query
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.retrieval_service import retrieval_service


class WorkspaceSearchTool:
    name = "workspace_search"
    label = "Workspace document search"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        retrieval_service.ensure_workspace_index(state.workspace_id, db)

        if is_overview_query(state.query) or state.document_scoped:
            contexts, citations = retrieval_service.get_workspace_overview(
                state.workspace_id,
                top_k=max(state.top_k, 12),
            )
        else:
            contexts, citations = retrieval_service.search(
                state.workspace_id,
                state.query,
                top_k=state.top_k,
            )

        state.contexts = contexts
        state.citations = list(citations)

        summary = (
            f"Found {len(contexts)} relevant chunk(s) across workspace documents"
            if contexts
            else "No indexed documents found in workspace"
        )
        state.steps.append(_step(self.name, self.label, summary, started))
        return state


workspace_search_tool = WorkspaceSearchTool()
