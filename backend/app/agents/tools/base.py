from __future__ import annotations

import time
from typing import Protocol

from sqlalchemy.orm import Session

from app.agents.state import AgentState
from app.schemas.search import AgentStepResponse, CitationResponse


class AgentTool(Protocol):
    name: str
    label: str

    def run(self, state: AgentState, db: Session) -> AgentState: ...


def _step(name: str, label: str, summary: str, started: float, status: str = "completed") -> AgentStepResponse:
    return AgentStepResponse(
        name=name,
        label=label,
        status=status,
        summary=summary,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
