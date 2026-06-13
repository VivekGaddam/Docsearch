from pydantic import BaseModel

from app.schemas.common import TimestampedSchema
from app.schemas.search import CitationResponse


class ResearchRequest(BaseModel):
    workspace_id: str
    query: str
    session_title: str


class ResearchResponse(TimestampedSchema):
    workspace_id: str
    user_id: str
    title: str
    query: str
    summary: str | None = None
    status: str


class ResearchReportResponse(BaseModel):
    session: ResearchResponse
    report_markdown: str
    citations: list[CitationResponse]

