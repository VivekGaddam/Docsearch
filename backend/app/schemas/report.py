from pydantic import BaseModel

from app.schemas.common import TimestampedSchema


class ReportCreateRequest(BaseModel):
    workspace_id: str
    research_session_id: str | None = None
    title: str
    format: str = "markdown"
    content: str


class ReportResponse(TimestampedSchema):
    workspace_id: str
    research_session_id: str | None = None
    title: str
    format: str
    content: str
    storage_path: str | None = None

