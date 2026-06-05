from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any, Literal, List

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
    raw_json: Optional[Dict[str, Any]] = None
    search_config_id: Optional[int] = None
    search_run_id: Optional[int] = None

class ContentItemCreate(ContentItemBase):
    """
    Schema for content creation/ingestion.
    Blocks the client (n8n) from defining curation status or notes.
    """
    pass

class ContentItemIngest(ContentItemCreate):
    """
    Alias for content ingestion.
    """
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
    raw_json: Optional[Dict[str, Any]] = None

class ContentItemStatusUpdate(BaseModel):
    status: Literal["new", "reviewed", "selected", "rejected", "produced", "archived"]

class ContentItemCurationUpdate(BaseModel):
    status: Optional[Literal["new", "reviewed", "selected", "rejected", "produced", "archived"]] = None
    notes: Optional[str] = None
    production_notes: Optional[str] = None
    rejected_reason: Optional[str] = None

class ContentItemRead(ContentItemBase):
    id: int
    status: str
    notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    selected_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    production_notes: Optional[str] = None
    collected_at: datetime
    last_seen_at: datetime

    class Config:
        from_attributes = True

# Alias for backward compatibility
ContentItem = ContentItemRead

class ContentItemListResponse(BaseModel):
    items: List[ContentItemRead]
    total: int
    limit: int
    offset: int

class ContentItemSummary(BaseModel):
    total_items: int
    new_items: int
    items_by_source: Dict[str, int]
    max_score: float
    max_views: int
