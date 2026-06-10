from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

# Video Project schemas
class VideoProjectCreate(BaseModel):
    title: str
    working_title: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    target_platform: Optional[str] = None
    video_format: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    status: Optional[str] = "idea"
    priority: Optional[int] = 0
    thumbnail_url: Optional[str] = None
    notes: Optional[str] = None

class VideoProjectUpdate(BaseModel):
    title: Optional[str] = None
    working_title: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    target_platform: Optional[str] = None
    video_format: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    thumbnail_url: Optional[str] = None
    script_text: Optional[str] = None
    script_content_json: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class VideoProjectRead(BaseModel):
    id: int
    title: str
    working_title: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    target_platform: Optional[str] = None
    video_format: Optional[str] = None
    target_duration_seconds: Optional[int] = None
    status: str
    priority: int
    thumbnail_url: Optional[str] = None
    script_text: str
    script_content_json: Optional[Dict[str, Any]] = None
    word_count: int
    estimated_duration_seconds: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoProjectListResponse(BaseModel):
    items: List[VideoProjectRead]
    total: int
    limit: int
    offset: int


# Video Project Note schemas (legacy — kept for backward compat)
class VideoProjectNoteCreate(BaseModel):
    note_type: Optional[str] = "idea"
    title: Optional[str] = None
    body: str
    status: Optional[str] = "open"
    pinned: Optional[bool] = False

class VideoProjectNoteUpdate(BaseModel):
    note_type: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None
    pinned: Optional[bool] = None

class VideoProjectNoteRead(BaseModel):
    id: int
    video_project_id: int
    note_type: str
    title: Optional[str] = None
    body: str
    status: str
    pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Video Project Reference schemas (legacy — kept for backward compat)
class VideoProjectReferenceCreate(BaseModel):
    content_item_id: Optional[int] = None
    reference_source_id: Optional[int] = None
    transcript_id: Optional[int] = None
    external_url: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None

class VideoProjectReferenceRead(BaseModel):
    id: int
    video_project_id: int
    content_item_id: Optional[int] = None
    reference_source_id: Optional[int] = None
    transcript_id: Optional[int] = None
    external_url: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Video Project Audio Idea schemas (legacy — kept for backward compat)
class VideoProjectAudioIdeaCreate(BaseModel):
    audio_title: Optional[str] = None
    audio_url: Optional[str] = None
    audio_type: Optional[str] = None
    mood: Optional[str] = None
    source_platform: Optional[str] = None
    license_notes: Optional[str] = None
    usage_notes: Optional[str] = None

class VideoProjectAudioIdeaRead(BaseModel):
    id: int
    video_project_id: int
    audio_title: Optional[str] = None
    audio_url: Optional[str] = None
    audio_type: Optional[str] = None
    mood: Optional[str] = None
    source_platform: Optional[str] = None
    license_notes: Optional[str] = None
    usage_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── VideoProjectItem schemas (unified workshop elements) ────────────────────

VALID_ITEM_TYPES = (
    "note", "reference", "script_excerpt", "audio",
    "thumbnail", "production", "todo", "image", "other"
)

class VideoProjectItemCreate(BaseModel):
    item_type: Optional[str] = "note"
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    source_kind: Optional[str] = "manual"
    source_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = "open"
    pinned: Optional[bool] = False

class VideoProjectItemUpdate(BaseModel):
    item_type: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    source_kind: Optional[str] = None
    source_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    pinned: Optional[bool] = None

class VideoProjectItemRead(BaseModel):
    id: int
    video_project_id: int
    item_type: str
    title: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    source_kind: Optional[str] = None
    source_id: Optional[int] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: str
    pinned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoProjectItemFromScriptExcerpt(BaseModel):
    text: str
    title: Optional[str] = None


# ─── External Boards ─────────────────────────────────────────────────────────

class ExternalBoardCreateRequest(BaseModel):
    provider: Optional[str] = "canva"


class ExternalBoardRead(BaseModel):
    id: int
    video_project_id: int
    provider: str
    external_id: str
    title: Optional[str] = None
    view_url: Optional[str] = None
    edit_url: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExternalBoardSyncResponse(BaseModel):
    board: ExternalBoardRead
    provider: str
    pushed_item_count: int
    sections_count: int
    duplicated_warning: bool = True
    synced_at: datetime
    message: str
