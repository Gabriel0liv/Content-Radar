from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.ideas import IdeaCreate, IdeaListResponse, IdeaRead, IdeaUpdate
from src.services.ideas_service import IdeasService

router = APIRouter()


@router.post("/video-projects", response_model=IdeaRead, status_code=status.HTTP_201_CREATED)
def create_idea(payload: IdeaCreate, db: Session = Depends(get_db)):
    return IdeasService(db).create(payload)


@router.get("/video-projects", response_model=IdeaListResponse)
def list_ideas(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    niche: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    items, total = IdeasService(db).list(
        limit=limit,
        offset=offset,
        search=search,
        status=status_filter,
        niche=niche,
    )
    return IdeaListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/video-projects/{id}", response_model=IdeaRead)
def get_idea(id: int, db: Session = Depends(get_db)):
    idea = IdeasService(db).get(id)
    if not idea:
        raise HTTPException(status_code=404, detail="Ideia não encontrada")
    return idea


@router.patch("/video-projects/{id}", response_model=IdeaRead)
def update_idea(id: int, payload: IdeaUpdate, db: Session = Depends(get_db)):
    idea = IdeasService(db).update(id, payload)
    if not idea:
        raise HTTPException(status_code=404, detail="Ideia não encontrada")
    return idea


@router.post("/video-projects/{id}/archive", response_model=IdeaRead)
def archive_idea(id: int, db: Session = Depends(get_db)):
    idea = IdeasService(db).archive(id)
    if not idea:
        raise HTTPException(status_code=404, detail="Ideia não encontrada")
    return idea


@router.delete("/video-projects/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_idea(id: int, db: Session = Depends(get_db)):
    if not IdeasService(db).delete(id):
        raise HTTPException(status_code=404, detail="Ideia não encontrada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
