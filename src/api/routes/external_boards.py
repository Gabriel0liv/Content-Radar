from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.video_workshop import ExternalBoardRead, ExternalBoardSyncResponse
from src.services.external_boards_service import ExternalBoardsService


router = APIRouter()


@router.get("/video-projects/{id}/external-boards", response_model=list[ExternalBoardRead])
def list_external_boards(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    return service.get_external_boards_for_project(id)


@router.post("/video-projects/{id}/external-boards/miro", response_model=ExternalBoardRead, status_code=status.HTTP_201_CREATED)
def create_miro_board(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    try:
        return service.create_miro_board_for_project(id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        detail = str(exc)
        if detail == "Miro não configurado":
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)


@router.post("/video-projects/{id}/external-boards/{board_id}/sync-to-miro", response_model=ExternalBoardSyncResponse)
def sync_external_board_to_miro(id: int, board_id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    try:
        return service.sync_project_items_to_miro(id, board_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        detail = str(exc)
        if detail == "Miro não configurado":
            raise HTTPException(status_code=400, detail=detail)
        raise HTTPException(status_code=502, detail=detail)


@router.delete("/external-boards/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_external_board(id: int, db: Session = Depends(get_db)):
    service = ExternalBoardsService(db)
    success = service.delete_external_board(id)
    if not success:
        raise HTTPException(status_code=404, detail="Board externo não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
