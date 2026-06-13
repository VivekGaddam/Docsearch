from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.report import ReportCreateRequest, ReportResponse
from app.services.report_service import report_service


router = APIRouter()


@router.get("/{workspace_id}", response_model=list[ReportResponse])
def get_reports(
    workspace_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return report_service.list_reports(workspace_id, user, db)


@router.post("", response_model=ReportResponse)
def post_report(
    payload: ReportCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return report_service.create_report(payload, user, db)

