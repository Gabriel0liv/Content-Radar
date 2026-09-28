from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SttResolvedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = "medium"
    language: str | None = None
    device: str = "auto"
    compute_type: str = "int8"
    batch_size: int = Field(default=2, ge=1)
    no_diarization: bool = True
    num_speakers: int | None = Field(default=None, ge=1)
    min_speakers: int | None = Field(default=None, ge=1)
    max_speakers: int | None = Field(default=None, ge=1)
    speaker_profile: str | None = None
    formats: str = "txt json srt vtt"
    export_formats: list[str] = Field(default_factory=lambda: ["txt", "json", "srt", "vtt"])
    vad_onset: float = Field(default=0.5, ge=0, le=1)
    vad_offset: float = Field(default=0.363, ge=0, le=1)
    chunk_size: int = Field(default=30, ge=1)
    initial_prompt: str | None = None
    diarize_model: str = "pyannote/speaker-diarization-3.1"
    offline: bool = False
    cache_dir: str | None = None


class NormalizedWord(BaseModel):
    word: str
    start: float | None = None
    end: float | None = None
    score: float | None = None
    speaker: str | None = None


class NormalizedSegment(BaseModel):
    index: int
    start: float | None = None
    end: float | None = None
    text: str
    speaker: str | None = None
    words: list[NormalizedWord] = Field(default_factory=list)


class NormalizedTranscriptResult(BaseModel):
    language: str | None = None
    engine: str = "whisperx"
    model: str
    full_text: str
    segments: list[NormalizedSegment]
    diarized: bool = False
    alignment_used: bool = False
    warnings: list[str] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)
