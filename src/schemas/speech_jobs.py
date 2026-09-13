from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.speech import SpeechSttPresetName


class SpeechSttJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: SpeechSttPresetName = "balanced"
    language: str | None = None
    diarization: bool = False
    num_speakers: int | None = Field(default=None, ge=1)
    min_speakers: int | None = Field(default=None, ge=1)
    max_speakers: int | None = Field(default=None, ge=1)
    quiet_speech: bool = False
    initial_prompt: str | None = None
    reference_source_id: int | None = None

    @model_validator(mode="after")
    def validate_speaker_range(self):
        if (
            self.num_speakers is None
            and self.min_speakers is not None
            and self.max_speakers is not None
            and self.min_speakers > self.max_speakers
        ):
            raise ValueError("min_speakers não pode ser maior que max_speakers")
        return self


class SpeechJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operation: Literal["stt", "tts"]
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    stage: str
    progress_percent: int
    progress_message: str | None = None
    requested_config_json: dict[str, Any]
    resolved_config_json: dict[str, Any] | None = None
    reference_source_id: int | None = None
    transcript_id: int | None = None
    worker_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class SpeechQueueStatus(BaseModel):
    queued: int = 0
    running: int = 0


class SpeechWorkerStatus(BaseModel):
    online: bool
    worker_id: str | None = None
    last_heartbeat_at: datetime | None = None
    capabilities: dict[str, Any] | None = None


class SpeechStatusRead(BaseModel):
    mode: Literal["native"] = "native"
    queue: SpeechQueueStatus
    worker: SpeechWorkerStatus
