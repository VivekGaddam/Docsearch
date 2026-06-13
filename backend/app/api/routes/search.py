from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.search import SearchRequest, SearchResultResponse
from app.services.agent_service import agent_service


router = APIRouter()


@router.post("", response_model=SearchResultResponse)
def search_workspace(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return agent_service.answer_query(payload, user, db)

