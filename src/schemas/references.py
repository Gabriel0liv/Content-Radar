from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re


YOUTUBE_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_youtube_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().split(":")[0]
    candidate: Optional[str] = None
    if host in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        path_parts = [part for part in parsed.path.split("/") if part]
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [None])[0]
        elif len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            candidate = path_parts[1]
    if not candidate or not YOUTUBE_VIDEO_ID_RE.fullmatch(candidate):
        raise ValueError("URL do YouTube inválida ou ID do vídeo não suportado")
    return candidate


class ReferenceSourceCreate(BaseModel):
    source_type: Literal["youtube_video", "manual"]
    source_url: str
    external_id: Optional[str] = None
    youtube_video_id: Optional[str] = None
    title: str
    channel_title: Optional[str] = None
    channel_id: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    status: str = "new"
    notes: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None


class ReferenceSourceUpdate(BaseModel):
    title: Optional[str] = None
    channel_title: Optional[str] = None
    channel_id: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None


class YouTubeUrlImportRequest(BaseModel):
    url: str
    preferred_languages: List[str] = Field(default_factory=lambda: ["pt", "pt-BR", "en"])
    allow_auto_captions: bool = True
    transcription_mode: Literal["auto", "max_fidelity"] = "auto"


class ReferenceSourceRead(BaseModel):
    id: int
    source_type: str
    source_url: str
    external_id: Optional[str] = None
    youtube_video_id: Optional[str] = None
    title: str
    channel_title: Optional[str] = None
    channel_id: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    thumbnail_url: Optional[str] = None
    language: Optional[str] = None
    status: str
    notes: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReferenceSourceListResponse(BaseModel):
    items: List[ReferenceSourceRead]
    total: int


class ReferenceImportJobRead(BaseModel):
    id: int
    reference_source_id: Optional[int] = None
    source_url: str
    status: str
    method: str
    preferred_languages: Optional[List[str]] = None
    selected_language: Optional[str] = None
    selected_caption_type: Optional[str] = None
    error_message: Optional[str] = None
    raw_result_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TranscriptSegmentCreate(BaseModel):
    segment_index: int
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker: Optional[str] = None
    text: str
    tokens_json: Optional[Dict[str, Any]] = None


class TranscriptSegmentRead(BaseModel):
    id: int
    transcript_id: int
    segment_index: int
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker: Optional[str] = None
    text: str
    tokens_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptCreate(BaseModel):
    language: Optional[str] = None
    source_method: Literal["manual_caption", "auto_caption", "manual", "audio_to_text_future", "whisperx"]
    full_text: str
    srt_text: Optional[str] = None
    vtt_text: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    segments: Optional[List[TranscriptSegmentCreate]] = None


class TranscriptRead(BaseModel):
    id: int
    reference_source_id: int
    import_job_id: Optional[int] = None
    language: Optional[str] = None
    source_method: str
    full_text: str
    full_text_hash: str
    srt_text: Optional[str] = None
    vtt_text: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    version_number: int
    is_active: bool
    duplicate_of_transcript_id: Optional[int] = None

    class Config:
        from_attributes = True


class TranscriptListResponse(BaseModel):
    transcripts: List[TranscriptRead]
    total: int