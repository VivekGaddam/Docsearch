from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas.search import AgentStepResponse, CitationResponse


@dataclass
class AgentState:
    query: str
    workspace_id: str
    include_web: bool = True
    top_k: int = 5

    plan: list[str] = field(default_factory=list)
    steps: list[AgentStepResponse] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)
    citations: list[CitationResponse] = field(default_factory=list)
    answer: str = ""
    mode: str = "agent"

    is_greeting: bool = False
    use_web: bool = False
    use_comparison: bool = False
    document_scoped: bool = False

    # ── Intent Classification ──────────────────────────────────────
    # Set by IntentClassifier; used by TaskRouter + ReasoningEngine
    intent: str = "general"           # summarize | compare | extract | research | explain | qa | general | greeting
    task_type: str = "general"        # matches intent; used for specialist agent routing
    sub_queries: list[str] = field(default_factory=list)   # decomposed sub-questions
    confidence: float = 1.0           # 0–1 classifier confidence

    # ── Reasoning Chain ───────────────────────────────────────────
    reasoning_chain: list[dict[str, str]] = field(default_factory=list)
    # e.g. [{"step": "Analyze evidence", "thought": "The document says…", "conclusion": "…"}]

    evidence_gaps: list[str] = field(default_factory=list)
    # Gaps the reasoning engine detected — "No mention of salary", etc.

    _user: Any = field(default=None, repr=False)

