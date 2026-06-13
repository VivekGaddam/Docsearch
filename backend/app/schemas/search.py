from pydantic import BaseModel


class SearchRequest(BaseModel):
    workspace_id: str
    query: str
    top_k: int = 5
    include_web: bool = True


class CitationResponse(BaseModel):
    document_name: str
    page_number: int | None = None
    chunk_reference: str
    chunk_id: str | None = None
    source_type: str = "document"
    url: str | None = None


class AgentStepResponse(BaseModel):
    name: str
    label: str
    status: str
    summary: str
    duration_ms: int | None = None


class ReasoningStep(BaseModel):
    step: str
    thought: str
    conclusion: str


class SearchResultResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    run_id: str
    plan: list[str]
    steps: list[AgentStepResponse] = []
    mode: str = "rag"
    # ── Reasoning & Intent fields ──────────────────────────────────
    intent: str = "general"
    task_type: str = "general"
    confidence: float = 1.0
    reasoning_chain: list[ReasoningStep] = []
    evidence_gaps: list[str] = []
    sub_queries: list[str] = []

