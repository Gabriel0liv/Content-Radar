from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SpeechExportFormat = Literal["txt", "json", "srt", "vtt"]


class SpeechSttJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: str = Field(default="balanced", min_length=1, max_length=200)
    language: str | None = Field(default=None, min_length=2, max_length=32)
    diarization: bool = False
    num_speakers: int | None = Field(default=None, ge=1)
    min_speakers: int | None = Field(default=None, ge=1)
    max_speakers: int | None = Field(default=None, ge=1)
    quiet_speech: bool = False
    initial_prompt: str | None = Field(default=None, max_length=8000)
    reference_source_id: int | None = None

    model: str | None = Field(default=None, min_length=1, max_length=100)
    device: Literal["auto", "cuda", "cpu"] | None = None
    compute_type: Literal["int8", "float16", "float32"] | None = None
    batch_size: int | None = Field(default=None, ge=1, le=128)
    vad_onset: float | None = Field(default=None, ge=0.0, le=1.0)
    vad_offset: float | None = Field(default=None, ge=0.0, le=1.0)
    chunk_size: int | None = Field(default=None, ge=5, le=600)
    diarize_model: str | None = Field(default=None, min_length=1, max_length=500)
    offline: bool | None = None
    cache_dir: str | None = Field(default=None, min_length=1, max_length=2000)
    export_formats: list[SpeechExportFormat] | None = None

    @model_validator(mode="after")
    def validate_speaker_range(self):
        if (
            self.num_speakers is None
            and self.min_speakers is not None
            and self.max_speakers is not None
            and self.min_speakers > self.max_speakers
        ):
            raise ValueError("min_speakers não pode ser maior que max_speakers")
        if self.export_formats is not None and not self.export_formats:
            raise ValueError("export_formats não pode ser vazio")
        return self


class SpeechTtsJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=200_000)
    engine: Literal["kokoro", "piper"]
    voice: str = Field(min_length=1, max_length=200)
    output_format: Literal["wav", "mp3"] = "wav"
    speed: float = Field(default=1.0, gt=0, le=3.0)
    language: str = Field(default="pt-br", min_length=2, max_length=32)
    normalize_ptbr: bool = False
    analyze_ptbr: bool = False
    preset: str | None = Field(default=None, min_length=1, max_length=200)
    preview: bool = False
    preview_chars: int = Field(default=300, ge=10, le=2000)


class SpeechVoiceSampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str | None = Field(default=None, min_length=1, max_length=5000)


class SpeechVoiceCompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=20_000)
    voice_ids: list[str] | None = None
    language: str = Field(default="pt-br", min_length=2, max_length=32)
    markdown_report: bool = True

    @model_validator(mode="after")
    def validate_voice_ids(self):
        if self.voice_ids is not None:
            normalized = [voice_id.strip() for voice_id in self.voice_ids]
            if any(not voice_id for voice_id in normalized):
                raise ValueError("voice_ids não pode conter valores vazios")
            if len(normalized) > 100:
                raise ValueError("voice_ids excede o limite")
            self.voice_ids = normalized
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
    result_json: dict[str, Any] | None = None
    reference_source_id: int | None = None
    transcript_id: int | None = None
    retry_of_job_id: int | None = None
    worker_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    archived_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class SpeechArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    speech_job_id: int
    artifact_type: str
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime


class SpeechSpeakerMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    raw_speaker: str
    display_name: str


class SpeechSpeakerMappingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=200)


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
