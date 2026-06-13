"""
ExtractAgent — Structured entity and data extraction specialist.

Retrieves the full document and primes the reasoning engine to produce
structured lists of entities, key facts, or data points rather than prose.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.specialist.base_agent import SpecialistAgent
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.retrieval_service import retrieval_service


class ExtractAgent(SpecialistAgent):
    name = "extract_agent"
    label = "Structured extraction"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        retrieval_service.ensure_workspace_index(state.workspace_id, db)

        # Use full overview for extraction — we need to see all mentions
        contexts, citations = retrieval_service.get_workspace_overview(
            state.workspace_id,
            top_k=max(state.top_k, 12),
        )

        state.contexts = contexts
        state.citations = list(citations)

        # Injection: tell the reasoning engine what kind of extraction is needed
        if not state.sub_queries or state.sub_queries == [state.query]:
            state.sub_queries = [
                f"List all entities mentioned related to: {state.query}",
                f"Extract all relevant facts and figures for: {state.query}",
                f"Identify any dates, names, and numbers relevant to: {state.query}",
            ]

        state.steps.append(_step(
            self.name,
            self.label,
            f"Retrieved {len(contexts)} chunk(s) for structured extraction",
            started,
        ))
        return state
