from __future__ import annotations

from typing import Iterator, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.speech_jobs import (
    SpeechJobRead,
    SpeechStatusRead,
    SpeechSttJobCreate,
    SpeechTtsJobCreate,
    SpeechVoiceCompareRequest,
    SpeechVoiceSampleRequest,
)
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


def _parse_export_formats(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@router.post("/jobs/stt", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_stt_job(request: SpeechSttJobCreate, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    raise HTTPException(status_code=400, detail="STT manual exige um arquivo. Use /speech/jobs/stt/upload.")


@router.post("/jobs/stt/upload", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def upload_stt_job(
    file: UploadFile = File(...),
    preset: str = Form("balanced"),
    language: str | None = Form(None),
    diarization: bool = Form(False),
    num_speakers: int | None = Form(None),
    min_speakers: int | None = Form(None),
    max_speakers: int | None = Form(None),
    quiet_speech: bool = Form(False),
    initial_prompt: str | None = Form(None),
    reference_source_id: int | None = Form(None),
    model: str | None = Form(None),
    device: Literal["auto", "cuda", "cpu"] | None = Form(None),
    compute_type: Literal["int8", "float16", "float32"] | None = Form(None),
    batch_size: int | None = Form(None),
    vad_onset: float | None = Form(None),
    vad_offset: float | None = Form(None),
    chunk_size: int | None = Form(None),
    diarize_model: str | None = Form(None),
    offline: bool | None = Form(None),
    cache_dir: str | None = Form(None),
    export_formats: str | None = Form(None),
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
            model=model,
            device=device,
            compute_type=compute_type,
            batch_size=batch_size,
            vad_onset=vad_onset,
            vad_offset=vad_offset,
            chunk_size=chunk_size,
            diarize_model=diarize_model,
            offline=offline,
            cache_dir=cache_dir,
            export_formats=_parse_export_formats(export_formats),
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    try:
        return service.create_uploaded_stt_job(request, filename=file.filename, chunks=_upload_chunks(file))
    except SpeechReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/tts", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_tts_job(request: SpeechTtsJobCreate, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        return service.create_tts_job(request.model_copy(update={"preview": False}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/tts/preview", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_tts_preview_job(request: SpeechTtsJobCreate, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        return service.create_tts_job(request.model_copy(update={"preview": True}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/tts/voice-samples/{voice_id}", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_voice_sample_job(voice_id: str, request: SpeechVoiceSampleRequest, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        return service.create_voice_sample_job(voice_id, text=request.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/tts/voice-samples", response_model=list[SpeechJobRead], status_code=status.HTTP_201_CREATED)
def create_all_voice_sample_jobs(request: SpeechVoiceSampleRequest, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        return service.create_all_voice_sample_jobs(text=request.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/tts/voice-compare", response_model=SpeechJobRead, status_code=status.HTTP_201_CREATED)
def create_voice_compare_job(request: SpeechVoiceCompareRequest, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        return service.create_voice_compare_job(text=request.text, voice_ids=request.voice_ids, language=request.language, markdown_report=request.markdown_report)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[SpeechJobRead])
def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    operation: Literal["stt", "tts"] | None = Query(None),
    job_status: Literal["queued", "running", "completed", "failed", "cancelled"] | None = Query(None, alias="status"),
    include_archived: bool = Query(False),
    service: SpeechJobsService = Depends(get_speech_jobs_service),
):
    return service.list_jobs(limit, operation=operation, status=job_status, include_archived=include_archived)


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


@router.post("/jobs/{job_id}/retry", status_code=status.HTTP_201_CREATED)
def retry_job(job_id: int, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    job = service.retry_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de áudio não encontrado")
    return job


@router.post("/jobs/{job_id}/archive")
def archive_job(job_id: int, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    job = service.archive_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job de áudio não encontrado")
    return {"id": job.id, "archived": True, "transcript_id": getattr(job, "transcript_id", None)}


@router.get("/jobs/{job_id}/artifacts/{artifact_id}/download")
def download_artifact(job_id: int, artifact_id: int, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        artifact, path = service.resolve_artifact_download(job_id, artifact_id)
        return FileResponse(path, media_type=artifact.mime_type or "application/octet-stream", filename=artifact.filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/jobs/{job_id}/artifacts/{artifact_id}")
def delete_artifact(job_id: int, artifact_id: int, service: SpeechJobsService = Depends(get_speech_jobs_service)):
    try:
        artifact = service.delete_artifact(job_id, artifact_id)
        return {"id": artifact.id, "deleted": True}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/status", response_model=SpeechStatusRead)
def get_status(service: SpeechJobsService = Depends(get_speech_jobs_service)):
    return service.get_status()
