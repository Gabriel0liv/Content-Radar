from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


SpeechSttPresetName = Literal["fast", "balanced", "max_quality"]


class SpeechSttOptions(BaseModel):
    preset: SpeechSttPresetName = "balanced"
    language: str | None = None
    identify_speakers: bool = False
    num_speakers: int | None = Field(default=None, ge=1)
    min_speakers: int | None = Field(default=None, ge=1)
    max_speakers: int | None = Field(default=None, ge=1)
    quiet_speech: bool = False
    initial_prompt: str | None = None

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


class ResolvedSpeechSttConfig(BaseModel):
    model: str
    language: str | None = None
    device: str = "auto"
    compute_type: str
    batch_size: int
    no_diarization: bool
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None
    speaker_profile: str | None = None
    formats: str = "txt json srt vtt"
    vad_onset: float
    vad_offset: float
    chunk_size: int = 30
    initial_prompt: str | None = None


class SpeechSttPresetSummary(BaseModel):
    name: SpeechSttPresetName
    label: str
    description: str


class SpeechEngineStatus(BaseModel):
    engine: str = "speech_studio"
    online: bool
    base_url: str
    message: str
    details: dict[str, Any] | None = None


class SpeechSttEngineResult(BaseModel):
    success: bool
    output_dir: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    logs: str = ""
    error: str | None = None
    message: str = ""
