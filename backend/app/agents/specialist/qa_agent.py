"""
QAAgent — Precise factoid Q&A + inference specialist.

Handles two types of QA:
1. Factoid — find the exact passage that answers the question
2. Inference/suitability — reason from evidence (e.g. "what companies can he apply for")

For inference questions, retrieves skills/experience sections specifically.
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.specialist.base_agent import SpecialistAgent
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.retrieval_service import retrieval_service

# Keywords that indicate an inference/suitability question
_INFERENCE_KEYWORDS = [
    "compan", "apply", "job", "role", "position", "hire", "suitable",
    "qualify", "fit", "eligible", "recruit", "career", "opportunit",
    "strength", "weakness", "good at", "expert", "best suited",
]

# Sub-queries for suitability inference
_SUITABILITY_SUB_QUERIES = [
    "What are the technical skills and technologies listed?",
    "What work experience and projects are described?",
    "What is the educational background and certifications?",
]


class QAAgent(SpecialistAgent):
    name = "qa_agent"
    label = "Q&A / Inference"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        retrieval_service.ensure_workspace_index(state.workspace_id, db)

        query_lower = state.query.lower()
        is_inference = any(kw in query_lower for kw in _INFERENCE_KEYWORDS)

        if is_inference:
            return self._run_inference(state, db, started)
        else:
            return self._run_factoid(state, db, started)

    def _run_factoid(self, state: AgentState, db: Session, started: float) -> AgentState:
        """Retrieve the most relevant passages to answer a direct question."""
        contexts, citations = retrieval_service.search(
            state.workspace_id,
            state.query,
            top_k=max(state.top_k, 6),
        )
        state.contexts = contexts
        state.citations = list(citations)

        if not state.sub_queries or state.sub_queries == [state.query]:
            state.sub_queries = [
                state.query,
                f"Supporting evidence for: {state.query}",
            ]

        state.steps.append(_step(
            self.name, self.label,
            f"Factoid Q&A: retrieved {len(contexts)} relevant chunk(s)",
            started,
        ))
        return state

    def _run_inference(self, state: AgentState, db: Session, started: float) -> AgentState:
        """
        Inference/suitability: run multiple targeted searches to gather
        skills, experience, and background evidence.
        """
        # Set suitability-focused sub-queries
        state.sub_queries = _SUITABILITY_SUB_QUERIES

        all_contexts: list[str] = []
        all_citations = []
        seen: set[str] = set()

        # Search for each sub-query to get different document sections
        sub_searches = [
            state.query,
            "skills technologies frameworks languages",
            "experience worked built delivered projects",
            "education certification background",
        ]

        for sq in sub_searches:
            ctxs, cits = retrieval_service.search(
                state.workspace_id, sq, top_k=3
            )
            for ctx, cit in zip(ctxs, cits):
                key = (cit.chunk_id or cit.chunk_reference)
                if key not in seen:
                    seen.add(key)
                    all_contexts.append(ctx)
                    all_citations.append(cit)

        state.contexts = all_contexts[:10]
        state.citations = all_citations[:10]

        state.steps.append(_step(
            self.name, self.label,
            f"Inference Q&A: gathered {len(state.contexts)} skill/experience chunk(s) for analysis",
            started,
        ))
        return state


qa_agent = QAAgent()
