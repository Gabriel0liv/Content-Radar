from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db.session import get_db
from src.schemas.video_workshop import (
    VideoProjectCreate,
    VideoProjectUpdate,
    VideoProjectRead,
    VideoProjectListResponse,
    VideoProjectNoteCreate,
    VideoProjectNoteUpdate,
    VideoProjectNoteRead,
    VideoProjectReferenceCreate,
    VideoProjectReferenceRead,
    VideoProjectAudioIdeaCreate,
    VideoProjectAudioIdeaRead,
    VideoProjectItemCreate,
    VideoProjectItemUpdate,
    VideoProjectItemRead,
    VideoProjectItemFromScriptExcerpt,
)
from src.services.video_workshop_service import VideoWorkshopService

router = APIRouter()

# --- Video Projects ---
@router.post("/video-projects", response_model=VideoProjectRead, status_code=status.HTTP_201_CREATED)
def create_video_project(payload: VideoProjectCreate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    return service.create_video_project(payload)

@router.get("/video-projects", response_model=VideoProjectListResponse)
def list_video_projects(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search by title, working title or description"),
    status: Optional[str] = Query(None),
    niche: Optional[str] = Query(None),
    video_format: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    service = VideoWorkshopService(db)
    items, total = service.list_video_projects(
        limit=limit,
        offset=offset,
        search=search,
        status=status,
        niche=niche,
        video_format=video_format
    )
    return VideoProjectListResponse(items=items, total=total, limit=limit, offset=offset)

@router.get("/video-projects/{id}", response_model=VideoProjectRead)
def get_video_project(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return project

@router.patch("/video-projects/{id}", response_model=VideoProjectRead)
def update_video_project(id: int, payload: VideoProjectUpdate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.update_video_project(id, payload)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return project

@router.post("/video-projects/{id}/archive", response_model=VideoProjectRead)
def archive_video_project(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.archive_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return project

@router.delete("/video-projects/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video_project(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    success = service.delete_video_project(id)
    if not success:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Notes ---
@router.get("/video-projects/{id}/notes", response_model=List[VideoProjectNoteRead])
def list_project_notes(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.list_notes_for_project(id)

@router.post("/video-projects/{id}/notes", response_model=VideoProjectNoteRead, status_code=status.HTTP_201_CREATED)
def create_project_note(id: int, payload: VideoProjectNoteCreate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.create_note_for_project(id, payload)

@router.patch("/video-project-notes/{id}", response_model=VideoProjectNoteRead)
def update_project_note(id: int, payload: VideoProjectNoteUpdate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    note = service.update_note(id, payload)
    if not note:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    return note

@router.delete("/video-project-notes/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_note(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    success = service.delete_note(id)
    if not success:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- References ---
@router.get("/video-projects/{id}/references", response_model=List[VideoProjectReferenceRead])
def list_project_references(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.list_references_for_project(id)

@router.post("/video-projects/{id}/references", response_model=VideoProjectReferenceRead, status_code=status.HTTP_201_CREATED)
def create_project_reference(id: int, payload: VideoProjectReferenceCreate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.create_reference_for_project(id, payload)

@router.delete("/video-project-references/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_reference(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    success = service.delete_reference(id)
    if not success:
        raise HTTPException(status_code=404, detail="Referência não encontrada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Audio Ideas ---
@router.get("/video-projects/{id}/audio-ideas", response_model=List[VideoProjectAudioIdeaRead])
def list_project_audio_ideas(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.list_audio_ideas_for_project(id)

@router.post("/video-projects/{id}/audio-ideas", response_model=VideoProjectAudioIdeaRead, status_code=status.HTTP_201_CREATED)
def create_project_audio_idea(id: int, payload: VideoProjectAudioIdeaCreate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.create_audio_idea_for_project(id, payload)

@router.delete("/video-project-audio-ideas/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_audio_idea(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    success = service.delete_audio_idea(id)
    if not success:
        raise HTTPException(status_code=404, detail="Ideia de áudio não encontrada")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Unified Workshop Items ---
@router.get("/video-projects/{id}/items", response_model=List[VideoProjectItemRead])
def list_project_items(
    id: int,
    item_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    pinned: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.list_items_for_project(id, item_type=item_type, status=status_filter, pinned=pinned)

@router.post("/video-projects/{id}/items", response_model=VideoProjectItemRead, status_code=status.HTTP_201_CREATED)
def create_project_item(id: int, payload: VideoProjectItemCreate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.create_item_for_project(id, payload)

@router.patch("/video-project-items/{id}", response_model=VideoProjectItemRead)
def update_project_item(id: int, payload: VideoProjectItemUpdate, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    item = service.update_item(id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Elemento da oficina não encontrado")
    return item

@router.delete("/video-project-items/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_item(id: int, db: Session = Depends(get_db)):
    service = VideoWorkshopService(db)
    success = service.delete_item(id)
    if not success:
        raise HTTPException(status_code=404, detail="Elemento da oficina não encontrado")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/video-projects/{id}/items/from-script-excerpt", response_model=VideoProjectItemRead, status_code=status.HTTP_201_CREATED)
def create_project_item_from_script_excerpt(
    id: int,
    payload: VideoProjectItemFromScriptExcerpt,
    db: Session = Depends(get_db)
):
    service = VideoWorkshopService(db)
    project = service.get_video_project(id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado")
    return service.create_item_from_script_excerpt(id, payload)
