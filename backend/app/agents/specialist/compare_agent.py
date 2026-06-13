"""
CompareAgent — Multi-document comparison specialist.

Retrieves content from multiple documents and structures the context
for comparative reasoning (similarities, differences, unique contributions).
"""
from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.specialist.base_agent import SpecialistAgent
from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.models.document import Document
from app.schemas.comparison import ComparisonRequest
from app.services.comparison_service import ComparisonService
from app.services.retrieval_service import retrieval_service


class CompareAgent(SpecialistAgent):
    name = "compare_agent"
    label = "Document comparison"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        retrieval_service.ensure_workspace_index(state.workspace_id, db)

        # Get workspace docs for comparison
        docs = (
            db.query(Document)
            .filter(Document.workspace_id == state.workspace_id)
            .order_by(Document.created_at.desc())
            .limit(4)
            .all()
        )

        if len(docs) < 2:
            # Fall back to regular search
            contexts, citations = retrieval_service.search(
                state.workspace_id, state.query, top_k=state.top_k
            )
            state.contexts = contexts
            state.citations = list(citations)
            state.steps.append(_step(
                self.name, self.label,
                "Fewer than 2 documents — falling back to regular search",
                started, status="skipped",
            ))
            return state

        # Run structured comparison for the two most recent docs
        user = getattr(state, "_user", None)
        if user:
            try:
                result = ComparisonService().compare_documents(
                    ComparisonRequest(
                        workspace_id=state.workspace_id,
                        left_document_id=docs[1].id,
                        right_document_id=docs[0].id,
                    ),
                    user=user,
                    db=db,
                )
                comparison_block = (
                    f"## Comparison: {docs[1].filename} vs {docs[0].filename}\n\n"
                    f"**Summary:** {result.summary}\n\n"
                    f"**Added sections:** {'; '.join(result.added_sections[:3]) or 'None'}\n\n"
                    f"**Removed sections:** {'; '.join(result.removed_sections[:3]) or 'None'}\n\n"
                    f"**Modified sections:** {'; '.join(result.modified_sections[:3]) or 'None'}"
                )
                state.contexts.append(comparison_block)
            except Exception:
                pass  # fall through to regular search

        # Also do a semantic search to get relevant passages
        contexts, citations = retrieval_service.search(
            state.workspace_id, state.query, top_k=state.top_k
        )
        state.contexts.extend(contexts)
        state.citations = list(citations)

        # Inject comparison sub-queries
        if not state.sub_queries or state.sub_queries == [state.query]:
            names = [d.filename for d in docs[:2]]
            state.sub_queries = [
                f"What are the key similarities between {names[0]} and {names[1]}?",
                f"What are the key differences between {names[0]} and {names[1]}?",
                f"Which document is more comprehensive or recent?",
            ]

        state.steps.append(_step(
            self.name,
            self.label,
            f"Compared {docs[1].filename} and {docs[0].filename}; retrieved {len(state.contexts)} context(s)",
            started,
        ))
        return state
