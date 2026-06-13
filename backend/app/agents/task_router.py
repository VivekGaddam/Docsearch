"""
Task Router — Routes classified intents to specialist agents.

Given a classified intent in AgentState, selects and runs the appropriate
specialist agent. Falls back to a general search when no specialist matches.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.specialist.base_agent import SpecialistAgent
from app.agents.specialist.compare_agent import CompareAgent
from app.agents.specialist.extract_agent import ExtractAgent
from app.agents.specialist.qa_agent import QAAgent
from app.agents.specialist.research_agent_specialist import ResearchSpecialistAgent
from app.agents.specialist.summarize_agent import SummarizeAgent
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.retrieval_service import retrieval_service
from app.services.web_search_service import web_search_service


# Registry: intent → specialist agent class
SPECIALIST_REGISTRY: dict[str, type[SpecialistAgent]] = {
    "summarize": SummarizeAgent,
    "compare":   CompareAgent,
    "research":  ResearchSpecialistAgent,
    "qa":        QAAgent,
    "extract":   ExtractAgent,
    # explain and general fall through to default search
}


class TaskRouter:
    """Routes an AgentState to the appropriate specialist agent and runs it."""

    def route(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()

        agent_class = SPECIALIST_REGISTRY.get(state.intent)

        if agent_class:
            specialist = agent_class()
            state.steps.append(_step(
                "task_router",
                "Route to specialist agent",
                f"Routed intent '{state.intent}' → {specialist.label}",
                started,
            ))
            return specialist.run(state, db)

        # Default: general workspace search + optional web
        return self._default_search(state, db, started)

    def _default_search(self, state: AgentState, db: Session, started: float) -> AgentState:
        """Fallback: standard workspace search (covers explain/general intents)."""
        retrieval_service.ensure_workspace_index(state.workspace_id, db)
        contexts, citations = retrieval_service.search(
            state.workspace_id, state.query, top_k=state.top_k
        )
        state.contexts = contexts
        state.citations = list(citations)

        if state.include_web and not state.document_scoped and (not contexts or state.intent == "research"):
            web_contexts, web_citations = web_search_service.search(state.query)
            state.contexts.extend(web_contexts)
            state.citations.extend(web_citations)

        state.steps.append(_step(
            "task_router",
            "Route to specialist agent",
            f"Intent '{state.intent}' → general search ({len(state.contexts)} context(s))",
            started,
        ))
        return state


task_router = TaskRouter()
