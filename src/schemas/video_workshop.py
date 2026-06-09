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


# Video Project Note schemas
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


# Video Project Reference schemas
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


# Video Project Audio Idea schemas
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


# Video Project Board Node schemas
class VideoProjectBoardNodeCreate(BaseModel):
    node_key: str
    node_type: Optional[str] = "note"
    title: Optional[str] = None
    body: Optional[str] = None
    x: float = 0.0
    y: float = 0.0
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    data_json: Optional[Dict[str, Any]] = None

class VideoProjectBoardNodeUpdate(BaseModel):
    node_type: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    data_json: Optional[Dict[str, Any]] = None

class VideoProjectBoardNodeRead(BaseModel):
    id: int
    video_project_id: int
    node_key: str
    node_type: str
    title: Optional[str] = None
    body: Optional[str] = None
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    color: Optional[str] = None
    data_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Video Project Board Edge schemas
class VideoProjectBoardEdgeCreate(BaseModel):
    edge_key: str
    source_node_key: str
    target_node_key: str
    label: Optional[str] = None
    data_json: Optional[Dict[str, Any]] = None

class VideoProjectBoardEdgeUpdate(BaseModel):
    label: Optional[str] = None
    data_json: Optional[Dict[str, Any]] = None

class VideoProjectBoardEdgeRead(BaseModel):
    id: int
    video_project_id: int
    edge_key: str
    source_node_key: str
    target_node_key: str
    label: Optional[str] = None
    data_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Unified Board State schema
class VideoProjectBoardStateRead(BaseModel):
    nodes: List[VideoProjectBoardNodeRead] = []
    edges: List[VideoProjectBoardEdgeRead] = []
