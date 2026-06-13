from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreateRequest


def list_workspaces(user: User, db: Session) -> list[Workspace]:
    return db.query(Workspace).filter(Workspace.owner_id == user.id).order_by(Workspace.created_at.desc()).all()


def create_workspace(payload: WorkspaceCreateRequest, user: User, db: Session) -> Workspace:
    workspace = Workspace(owner_id=user.id, name=payload.name, description=payload.description)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def get_workspace_for_user(workspace_id: str, user: User, db: Session) -> Workspace:
    workspace = (
        db.query(Workspace)
        .filter(Workspace.id == workspace_id, Workspace.owner_id == user.id)
        .first()
    )
    if not workspace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace

