from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.speech_jobs import SpeechJobRead, SpeechStatusRead, SpeechSttJobCreate
from src.services.speech_jobs_service import SpeechJobsService, SpeechReferenceNotFoundError


router = APIRouter()


def get_speech_jobs_service(db: Session = Depends(get_db)) -> SpeechJobsService:
    return SpeechJobsService(db)


@router.post("/jobs/stt", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_stt_job(
    request: SpeechSttJobCreate,
    service: SpeechJobsService = Depends(get_speech_jobs_service),
):
    try:
        return service.create_stt_job(request)
    except SpeechReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[SpeechJobRead])
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    service: SpeechJobsService = Depends(get_speech_jobs_service),
):
    return service.list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=SpeechJobRead)
def get_job(job_id: int, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de áudio não encontrado")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=SpeechJobRead)
def cancel_job(job_id: int, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    job = service.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de áudio não encontrado")
    return job


@router.get("/status", response_model=SpeechStatusRead)
def get_status(service: SpeechJobsService = Depends(get_speech_jobs_service)):
    return service.get_status()
