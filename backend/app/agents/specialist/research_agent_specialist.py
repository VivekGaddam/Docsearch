"""
ResearchSpecialistAgent — Multi-hop research specialist.

Handles complex research queries requiring:
- Sub-query decomposition (already set by IntentClassifier)
- Multi-hop retrieval: runs a search for EACH sub-query and merges results
- Web search augmentation when workspace evidence is thin
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.specialist.base_agent import SpecialistAgent
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.services.retrieval_service import retrieval_service
from app.services.web_search_service import web_search_service


class ResearchSpecialistAgent(SpecialistAgent):
    name = "research_agent"
    label = "Multi-hop research"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        retrieval_service.ensure_workspace_index(state.workspace_id, db)

        all_contexts: list[str] = []
        all_citations = []
        seen_chunks: set[str] = set()

        # Multi-hop: retrieve for each sub-query independently
        queries_to_run = state.sub_queries if state.sub_queries else [state.query]

        for sub_q in queries_to_run[:3]:
            contexts, citations = retrieval_service.search(
                state.workspace_id,
                sub_q,
                top_k=max(state.top_k, 4),
            )
            for ctx, cit in zip(contexts, citations):
                key = cit.chunk_reference
                if key not in seen_chunks:
                    seen_chunks.add(key)
                    all_contexts.append(ctx)
                    all_citations.append(cit)

        state.contexts = all_contexts
        state.citations = all_citations

        # Add web search results if enabled and workspace evidence is thin
        if state.include_web and (not all_contexts or len(all_contexts) < 3):
            web_contexts, web_citations = web_search_service.search(state.query)
            state.contexts.extend(web_contexts)
            state.citations.extend(web_citations)

        hop_count = len(queries_to_run)
        state.steps.append(_step(
            self.name,
            self.label,
            f"Multi-hop retrieval: {hop_count} sub-queries → {len(state.contexts)} unique context(s)",
            started,
        ))
        return state
