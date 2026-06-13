"""Abstract base class for all specialist agents."""
from __future__ import annotations

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from app.agents.state import AgentState


class SpecialistAgent(ABC):
    """Base class for task-specific specialist agents."""

    name: str = "specialist"
    label: str = "Specialist agent"

    @abstractmethod
    def run(self, state: AgentState, db: Session) -> AgentState:
        """Execute the specialist task and return updated state."""
        ...
