from __future__ import annotations

from typing import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.speech import SpeechSttPresetName
from src.schemas.speech_jobs import SpeechJobRead, SpeechStatusRead, SpeechSttJobCreate
from src.services.speech_jobs_service import SpeechJobsService, SpeechReferenceNotFoundError


router = APIRouter()


def get_speech_jobs_service(db: Session = Depends(get_db)) -> SpeechJobsService:
    return SpeechJobsService(db)


def _upload_chunks(file: UploadFile, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    while True:
        chunk = file.file.read(chunk_size)
        if not chunk:
            break
        yield chunk


@router.post("/jobs/stt", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_stt_job(
    request: SpeechSttJobCreate,
    service: SpeechJobsService = Depends(get_speech_jobs_service),
):
    raise HTTPException(
        status_code=400,
        detail="STT manual exige um arquivo. Use /speech/jobs/stt/upload.",
    )


@router.post("/jobs/stt/upload", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def upload_stt_job(
    file: UploadFile = File(...),
    preset: SpeechSttPresetName = Form("balanced"),
    language: str | None = Form(None),
    diarization: bool = Form(False),
    num_speakers: int | None = Form(None),
    min_speakers: int | None = Form(None),
    max_speakers: int | None = Form(None),
    quiet_speech: bool = Form(False),
    initial_prompt: str | None = Form(None),
    reference_source_id: int | None = Form(None),
    service: SpeechJobsService = Depends(get_speech_jobs_service),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo sem nome")
    try:
        request = SpeechSttJobCreate(
            preset=preset,
            language=language,
            diarization=diarization,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            quiet_speech=quiet_speech,
            initial_prompt=initial_prompt,
            reference_source_id=reference_source_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    try:
        return service.create_uploaded_stt_job(
            request,
            filename=file.filename,
            chunks=_upload_chunks(file),
        )
    except SpeechReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
