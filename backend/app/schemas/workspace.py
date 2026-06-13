from pydantic import BaseModel

from app.schemas.common import TimestampedSchema


class WorkspaceCreateRequest(BaseModel):
    name: str
    description: str | None = None


class WorkspaceResponse(TimestampedSchema):
    owner_id: str
    name: str
    description: str | None = None

