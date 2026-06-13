from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.web_search_service import web_search_service


class WebSearchTool:
    name = "web_search"
    label = "Web search"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        web_contexts, web_citations = web_search_service.search(state.query)
        state.contexts.extend(web_contexts)
        state.citations.extend(web_citations)
        state.steps.append(_step(
            self.name,
            self.label,
            f"Retrieved {len(web_contexts)} external source(s)",
            started,
        ))
        return state


web_search_tool = WebSearchTool()
