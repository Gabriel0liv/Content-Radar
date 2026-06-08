from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Literal

from src.db.session import get_db
from src.schemas.references import (
    ReferenceSourceCreate,
    ReferenceSourceUpdate,
    ReferenceSourceRead,
    ReferenceSourceListResponse,
    ReferenceImportJobRead,
    YouTubeUrlImportRequest,
    YouTubeUrlImportResponse,
    TranscriptCreate,
    TranscriptRead,
    TranscriptSegmentCreate,
    TranscriptSegmentRead
)
from src.services.references_service import ReferencesService

# Router 1: Reference Sources
reference_sources_router = APIRouter()

# Fixed/specific route MUST come before dynamic ID routes
@reference_sources_router.post("/import-youtube-url", response_model=YouTubeUrlImportResponse)
def import_youtube_url(
    payload: YouTubeUrlImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers YouTube reference url metadata and transcription import in the background.
    """
    service = ReferencesService(db)
    job = service.import_youtube_url(payload, background_tasks)
    return YouTubeUrlImportResponse(
        reference_source_id=job.reference_source_id,
        import_job_id=job.id,
        status=job.status
    )

@reference_sources_router.get("", response_model=ReferenceSourceListResponse)
def get_reference_sources(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search term for title, channel, description"),
    source_type: Optional[Literal["youtube_video", "manual"]] = None,
    status: Optional[str] = None,
    channel_title: Optional[str] = None,
    sort_by: Literal["created_at", "updated_at", "title", "view_count", "like_count", "duration_seconds", "published_at"] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db)
):
    """
    List reference sources with pagination, search, and ordering.
    """
    service = ReferencesService(db)
    items, total = service.list_reference_sources(
        limit=limit,
        offset=offset,
        search=search,
        source_type=source_type,
        status=status,
        channel_title=channel_title,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return ReferenceSourceListResponse(items=items, total=total, limit=limit, offset=offset)

@reference_sources_router.get("/{id}", response_model=ReferenceSourceRead)
def get_reference_source(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single reference source by ID.
    """
    service = ReferencesService(db)
    source = service.get_reference_source(id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte de referência não encontrada")
    return source

@reference_sources_router.patch("/{id}", response_model=ReferenceSourceRead)
def update_reference_source(id: int, payload: ReferenceSourceUpdate, db: Session = Depends(get_db)):
    """
    Update basic information of a reference source.
    """
    service = ReferencesService(db)
    source = service.update_reference_source(id, payload)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte de referência não encontrada")
    return source

@reference_sources_router.get("/{id}/transcripts", response_model=List[TranscriptRead])
def get_reference_source_transcripts(id: int, db: Session = Depends(get_db)):
    """
    Get transcripts registered under a reference source.
    """
    service = ReferencesService(db)
    source = service.get_reference_source(id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte de referência não encontrada")
    return service.get_transcripts_for_source(id)

@reference_sources_router.post("/{id}/transcripts", response_model=TranscriptRead)
def create_reference_source_transcript(id: int, payload: TranscriptCreate, db: Session = Depends(get_db)):
    """
    Allows posting a manual transcript or import to a reference source.
    """
    service = ReferencesService(db)
    source = service.get_reference_source(id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte de referência não encontrada")
    return service.create_manual_transcript(id, payload)

@reference_sources_router.get("/{id}/import-jobs", response_model=List[ReferenceImportJobRead])
def get_reference_source_import_jobs(id: int, db: Session = Depends(get_db)):
    """
    Fetch history of import jobs for a specific reference source.
    """
    service = ReferencesService(db)
    source = service.get_reference_source(id)
    if not source:
        raise HTTPException(status_code=404, detail="Fonte de referência não encontrada")
    return service.get_import_jobs_for_source(id)


# Router 2: Reference Import Jobs
reference_import_jobs_router = APIRouter()

@reference_import_jobs_router.get("/{id}", response_model=ReferenceImportJobRead)
def get_reference_import_job(id: int, db: Session = Depends(get_db)):
    """
    Track import job status. Used for polling by the frontend.
    """
    service = ReferencesService(db)
    job = service.get_import_job(id)
    if not job:
        raise HTTPException(status_code=404, detail="Job de importação não encontrado")
    return job


# Router 3: Transcripts
transcripts_router = APIRouter()

@transcripts_router.get("/{id}", response_model=TranscriptRead)
def get_transcript(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single transcript record.
    """
    service = ReferencesService(db)
    transcript = service.get_transcript(id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    return transcript

@transcripts_router.get("/{id}/segments", response_model=List[TranscriptSegmentRead])
def get_transcript_segments(id: int, db: Session = Depends(get_db)):
    """
    Fetch the segments (with timestamps) for a transcript.
    """
    service = ReferencesService(db)
    transcript = service.get_transcript(id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    return service.get_transcript_segments(id)

@transcripts_router.post("/{id}/segments/import", response_model=List[TranscriptSegmentRead])
def import_transcript_segments(id: int, segments: List[TranscriptSegmentCreate], db: Session = Depends(get_db)):
    """
    Import custom or bulk segments into a transcript manually.
    """
    service = ReferencesService(db)
    transcript = service.get_transcript(id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcrição não encontrada")
    return service.repo.create_transcript_segments(id, segments)
