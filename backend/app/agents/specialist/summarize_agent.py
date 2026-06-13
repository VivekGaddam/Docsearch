"""
SummarizeAgent — Deep document summarization specialist.

Adjusts retrieval to get broad coverage (higher top_k, overview mode),
then prepares the state for the ReasoningEngine with summarization-specific
sub-queries (key themes, main findings, author conclusions).
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.specialist.base_agent import SpecialistAgent
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.retrieval_service import retrieval_service


class SummarizeAgent(SpecialistAgent):
    name = "summarize_agent"
    label = "Deep summarization"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()

        # Expand retrieval for full document coverage
        retrieval_service.ensure_workspace_index(state.workspace_id, db)
        contexts, citations = retrieval_service.get_workspace_overview(
            state.workspace_id,
            top_k=max(state.top_k, 15),
        )

        state.contexts = contexts
        state.citations = list(citations)

        # Inject structured sub-queries for summarization reasoning
        if not state.sub_queries or state.sub_queries == [state.query]:
            state.sub_queries = [
                f"What are the main topics covered in the document?",
                f"What are the key findings or conclusions?",
                f"What is the overall structure and purpose of the document?",
            ]

        state.steps.append(_step(
            self.name,
            self.label,
            f"Retrieved {len(contexts)} chunks for comprehensive summarization",
            started,
        ))
        return state
