from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import comparison_service


router = APIRouter()


@router.post("", response_model=ComparisonResponse)
def compare_documents(
    payload: ComparisonRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return comparison_service.compare_documents(payload, user, db)

