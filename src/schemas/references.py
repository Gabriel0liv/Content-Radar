from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
import re

YT_VIDEO_ID_REGEX = re.compile(
    r'(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})'
)
YT_VIDEO_ID_ONLY_REGEX = re.compile(r'^[a-zA-Z0-9_-]{11}$')


def extract_youtube_video_id(url: str) -> str:
    if "/channel/" in url or "/c/" in url or "/user/" in url or "/@" in url:
        raise ValueError("URLs de canais ou perfis do YouTube não são suportadas. Por favor, envie a URL de um vídeo individual.")

    is_video_url = "watch?v=" in url or "youtu.be/" in url or "/shorts/" in url or "/embed/" in url
    if "playlist" in url or ("list=" in url and not is_video_url):
        raise ValueError("URLs de playlists não são suportadas. Por favor, envie a URL de um vídeo individual.")

    match = YT_VIDEO_ID_REGEX.search(url)
    if not match:
        raise ValueError("URL do YouTube inválida ou formato não suportado. Use links de vídeos normais ou Shorts.")
    return match.group(1)


def validate_youtube_video_id(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not YT_VIDEO_ID_ONLY_REGEX.fullmatch(normalized):
        raise ValueError("youtube_video_id deve conter exatamente um ID de vídeo válido do YouTube")
    return normalized


class YouTubeUrlImportRequest(BaseModel):
    url: str
    preferred_languages: List[str] = Field(default_factory=lambda: ["pt", "pt-BR", "en"])
    allow_auto_captions: bool = True
    transcription_mode: Literal["auto", "max_fidelity"] = "auto"

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        url = v.strip()
        extract_youtube_video_id(url)
        return url


class YouTubeUrlImportResponse(BaseModel):
    reference_source_id: Optional[int] = None
    import_job_id: int
    status: str


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
    status: Literal["new", "importing", "transcribed", "needs_audio_transcription", "failed", "archived"] = "new"
    notes: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None

    @field_validator("youtube_video_id")
    @classmethod
    def validate_canonical_youtube_video_id(cls, value: Optional[str]) -> Optional[str]:
        return validate_youtube_video_id(value)


class ReferenceSourceUpdate(BaseModel):
    title: Optional[str] = None
    channel_title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["new", "importing", "transcribed", "needs_audio_transcription", "failed", "archived"]] = None
    notes: Optional[str] = None
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    youtube_video_id: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    raw_json: Optional[Dict[str, Any]] = None

    @field_validator("youtube_video_id")
    @classmethod
    def validate_canonical_youtube_video_id(cls, value: Optional[str]) -> Optional[str]:
        return validate_youtube_video_id(value)


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
    limit: int
    offset: int


class ReferenceImportJobRead(BaseModel):
    id: int
    reference_source_id: Optional[int] = None
    source_url: str
    status: Literal["queued", "running", "completed", "failed", "needs_audio_transcription"]
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
