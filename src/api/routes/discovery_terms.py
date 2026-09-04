from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from src.db.session import get_db
from src.schemas.discovery_terms import DiscoveryTermRead
from src.services.discovery_terms_service import DiscoveryTermsService

router = APIRouter()


@router.get("", response_model=List[DiscoveryTermRead])
def get_discovery_terms(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return DiscoveryTermsService(db).search(q, limit)


@router.post("/rebuild")
def rebuild_discovery_terms(db: Session = Depends(get_db)):
    count = DiscoveryTermsService(db).rebuild()
    return {"rebuilt": count}
