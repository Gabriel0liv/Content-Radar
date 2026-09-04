from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.global_search import GlobalSearchResponse
from src.services.global_search_service import GlobalSearchService

router = APIRouter()


@router.get("", response_model=GlobalSearchResponse)
def global_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=25),
    db: Session = Depends(get_db),
):
    return GlobalSearchService(db).search(q, limit)
