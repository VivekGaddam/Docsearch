from sqlalchemy.orm import Session

from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportCreateRequest
from app.services.workspace_service import get_workspace_for_user


class ReportService:
    def create_report(self, payload: ReportCreateRequest, user: User, db: Session) -> Report:
        get_workspace_for_user(payload.workspace_id, user, db)
        report = Report(**payload.model_dump())
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    def list_reports(self, workspace_id: str, user: User, db: Session) -> list[Report]:
        get_workspace_for_user(workspace_id, user, db)
        return (
            db.query(Report)
            .filter(Report.workspace_id == workspace_id)
            .order_by(Report.created_at.desc())
            .all()
        )


report_service = ReportService()

