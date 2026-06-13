from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import DocumentResponse, UploadResponse
from app.services.ingestion_service import ingest_document, list_documents


router = APIRouter()


@router.get("/{workspace_id}", response_model=list[DocumentResponse])
def get_documents(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_documents(workspace_id, user, db)


@router.post("/{workspace_id}/upload", response_model=UploadResponse)
async def upload_document(
    workspace_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await ingest_document(workspace_id, file, user, db)

