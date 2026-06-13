from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.agents.tools.base import _step
from app.models.document import Document
from app.schemas.comparison import ComparisonRequest
from app.services.comparison_service import ComparisonService


class DocumentComparisonTool:
    name = "document_comparison"
    label = "Document comparison"

    def run(self, state: AgentState, db: Session) -> AgentState:
        started = time.perf_counter()
        user = getattr(state, "_user", None)
        if user is None:
            state.steps.append(_step(
                self.name, self.label, "Comparison skipped — no user context", started, status="skipped",
            ))
            return state

        docs = (
            db.query(Document)
            .filter(Document.workspace_id == state.workspace_id)
            .order_by(Document.created_at.desc())
            .limit(2)
            .all()
        )

        if len(docs) < 2:
            state.steps.append(_step(
                self.name, self.label,
                "Need at least 2 documents in workspace to compare — skipped",
                started, status="skipped",
            ))
            return state

        result = ComparisonService().compare_documents(
            ComparisonRequest(
                workspace_id=state.workspace_id,
                left_document_id=docs[1].id,
                right_document_id=docs[0].id,
            ),
            user=user,
            db=db,
        )

        comparison_text = (
            f"Comparison: {docs[1].filename} vs {docs[0].filename}\n"
            f"Summary: {result.summary}\n"
            f"Added: {'; '.join(result.added_sections[:2])}\n"
            f"Removed: {'; '.join(result.removed_sections[:2])}\n"
            f"Modified: {'; '.join(result.modified_sections[:2])}"
        )
        state.contexts.append(comparison_text)
        state.steps.append(_step(
            self.name,
            self.label,
            f"Compared {docs[1].filename} and {docs[0].filename}",
            started,
        ))
        return state


document_comparison_tool = DocumentComparisonTool()
