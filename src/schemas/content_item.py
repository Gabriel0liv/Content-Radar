from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any, List

class ContentItemBase(BaseModel):
    source: str
    external_id: str
    content_type: str = "video"
    title: str
    description: Optional[str] = None
    url: str
    channel_title: Optional[str] = None
    published_at: Optional[datetime] = None
    views: Optional[int] = 0
    likes: Optional[int] = 0
    comments: Optional[int] = 0
    views_per_day: Optional[float] = 0.0
    score: Optional[float] = 0.0
    topic_seed: Optional[str] = None
    discovery_query: Optional[str] = None
    language: Optional[str] = None
    country_code: Optional[str] = None
    status: Optional[str] = "new"
    notes: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    reviewed_at: Optional[datetime] = None
    selected_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    production_notes: Optional[str] = None

class ContentItemCreate(ContentItemBase):
    pass

class ContentItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    channel_title: Optional[str] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    views_per_day: Optional[float] = None
    score: Optional[float] = None
    topic_seed: Optional[str] = None
    discovery_query: Optional[str] = None
    language: Optional[str] = None
    country_code: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    rejected_reason: Optional[str] = None
    production_notes: Optional[str] = None

class ContentItemStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(new|reviewed|selected|rejected|produced|archived)$")

class ContentItem(ContentItemBase):
    id: int
    collected_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True

class ContentItemSummary(BaseModel):
    total_items: int
    new_items: int
    items_by_source: Dict[str, int]
    max_score: float
    max_views: int
