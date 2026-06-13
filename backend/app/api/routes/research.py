from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.research import ResearchReportResponse, ResearchRequest
from app.services.research_service import research_service


router = APIRouter()


@router.post("/runs", response_model=ResearchReportResponse)
def run_research(
    payload: ResearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return research_service.run_research(payload, user, db)

