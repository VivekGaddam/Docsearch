from difflib import SequenceMatcher

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.workspace_service import get_workspace_for_user


class ComparisonService:
    def compare_documents(
        self,
        payload: ComparisonRequest,
        user: User,
        db: Session,
    ) -> ComparisonResponse:
        get_workspace_for_user(payload.workspace_id, user, db)
        left = db.query(Document).filter(Document.id == payload.left_document_id).first()
        right = db.query(Document).filter(Document.id == payload.right_document_id).first()
        if not left or not right:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        left_chunks = db.query(Chunk).filter(Chunk.document_id == left.id).all()
        right_chunks = db.query(Chunk).filter(Chunk.document_id == right.id).all()
        left_text = "\n".join(chunk.content for chunk in left_chunks)
        right_text = "\n".join(chunk.content for chunk in right_chunks)

        matcher = SequenceMatcher(None, left_text, right_text)
        ratio = matcher.ratio()
        return ComparisonResponse(
            summary=f"Documents are {ratio:.1%} similar based on chunked text comparison.",
            added_sections=[chunk.content[:180] for chunk in right_chunks[:3]],
            removed_sections=[chunk.content[:180] for chunk in left_chunks[:3]],
            modified_sections=[
                "Use embedding-level section alignment and LLM summarization for production diffing."
            ],
        )


comparison_service = ComparisonService()

