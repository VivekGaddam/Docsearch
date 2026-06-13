from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceResponse
from app.services.workspace_service import create_workspace, list_workspaces


router = APIRouter()


@router.get("", response_model=list[WorkspaceResponse])
def get_workspaces(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return list_workspaces(user, db)


@router.post("", response_model=WorkspaceResponse)
def post_workspace(
    payload: WorkspaceCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return create_workspace(payload, user, db)

