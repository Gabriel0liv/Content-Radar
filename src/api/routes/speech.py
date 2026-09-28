from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.speech import SpeechSttOptions
from src.services.speech_presets import list_builtin_stt_presets, resolve_stt_config
from src.services.speech_presets_service import (
    BuiltinSpeechPresetError,
    DuplicateSpeechPresetError,
    InvalidSpeechPresetError,
    SpeechPresetError,
    SpeechPresetsService,
)
from src.services.speech_settings_service import InvalidSpeechSettingsError, SpeechSettingsService


router = APIRouter()


class SpeechPresetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    operation: Literal["stt", "tts"]
    config: dict[str, Any]
    description: str | None = Field(default=None, max_length=2000)


class SpeechPresetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=2000)


class SpeechSettingsUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_stt_preset: str | None = None
    default_language: str | None = None
    default_diarization: bool | None = None
    default_tts_engine: Literal["kokoro", "piper"] | None = None
    default_voice: str | None = None
    default_output_format: Literal["wav", "mp3"] | None = None
    default_ptbr_normalization: bool | None = None
    default_export_formats: list[Literal["txt", "json", "srt", "vtt"]] | None = None
    offline_mode: bool | None = None
    artifact_retention_days: int | None = Field(default=None, ge=0, le=3650)
    input_retention_days: int | None = Field(default=None, ge=0, le=3650)
    retain_debug_artifacts: bool | None = None
    hardware_policy: Literal["auto", "cuda", "cpu"] | None = None


def _presets_service(db: Session = Depends(get_db)) -> SpeechPresetsService:
    return SpeechPresetsService(db)


def _preset_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DuplicateSpeechPresetError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, BuiltinSpeechPresetError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, InvalidSpeechPresetError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/stt/presets")
def get_stt_presets():
    # Kept for compatibility with the existing STT client until the unified
    # /audio client switches to /speech/presets.
    return {"presets": list_builtin_stt_presets()}


@router.post("/stt/resolve")
def resolve_stt(options: SpeechSttOptions):
    resolved = resolve_stt_config(options)
    return {"options": options, "resolved": resolved}


@router.get("/presets")
def list_presets(
    operation: Literal["stt", "tts"] = Query(...),
    service: SpeechPresetsService = Depends(_presets_service),
):
    return {"presets": service.list_presets(operation)}


@router.post("/presets", status_code=status.HTTP_201_CREATED)
def create_preset(
    request: SpeechPresetCreateRequest,
    service: SpeechPresetsService = Depends(_presets_service),
):
    try:
        return service.create_preset(request.name, request.operation, request.config, request.description)
    except SpeechPresetError as exc:
        raise _preset_error(exc) from exc


@router.patch("/presets/{preset_id}")
def update_preset(
    preset_id: int,
    request: SpeechPresetUpdateRequest,
    service: SpeechPresetsService = Depends(_presets_service),
):
    try:
        return service.update_preset(
            preset_id,
            name=request.name,
            config=request.config,
            description=request.description,
        )
    except SpeechPresetError as exc:
        raise _preset_error(exc) from exc


@router.delete("/presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(preset_id: int, service: SpeechPresetsService = Depends(_presets_service)):
    try:
        deleted = service.delete_preset(preset_id)
    except SpeechPresetError as exc:
        raise _preset_error(exc) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="preset não encontrado")
    return None


@router.get("/settings")
def get_settings():
    try:
        return SpeechSettingsService().get_speech_settings()
    except InvalidSpeechSettingsError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/settings")
def update_settings(request: SpeechSettingsUpdateRequest):
    changes = request.model_dump(exclude_none=True)
    try:
        return SpeechSettingsService().update_speech_settings(changes)
    except InvalidSpeechSettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
