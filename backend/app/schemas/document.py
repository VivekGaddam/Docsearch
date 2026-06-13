from pydantic import BaseModel

from app.schemas.common import TimestampedSchema


class DocumentResponse(TimestampedSchema):
    workspace_id: str
    filename: str
    source_type: str
    mime_type: str | None = None
    storage_path: str | None = None
    status: str


class ChunkResponse(TimestampedSchema):
    workspace_id: str
    document_id: str
    chunk_id: str
    page_number: int | None = None
    content: str
    source_type: str


class UploadResponse(BaseModel):
    document: DocumentResponse
    ingested_chunks: int

