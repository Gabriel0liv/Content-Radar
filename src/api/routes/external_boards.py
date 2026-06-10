from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.video_workshop import ExternalBoardRead
from src.services.external_boards_service import ExternalBoardsService


router = APIRouter()


@router.get("/video-projects/{id}/external-boards", response_model=list[ExternalBoardRead])
def list_external_boards(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    try:
        return service.get_external_boards_for_project(id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/video-projects/{id}/external-boards/canva", response_model=ExternalBoardRead, status_code=status.HTTP_201_CREATED)
def create_canva_board(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    try:
        return service.create_canva_board_for_project(id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        detail = str(exc)
        if detail.startswith("Canva não configurado"):
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)


@router.post("/external-boards/{id}/refresh-canva-url", response_model=ExternalBoardRead)
def refresh_canva_url(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    try:
        return service.refresh_canva_design_urls(id)
    except ValueError as exc:
        detail = str(exc)
        if detail == "Refresh de URL suportado apenas para boards Canva":
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=404, detail=detail)
    except RuntimeError as exc:
        detail = str(exc)
        if detail.startswith("Canva não configurado"):
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)


@router.delete("/external-boards/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_external_board(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    success = service.delete_external_board(id)
    if not success:
        raise HTTPException(status_code=404, detail="Board externo não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
