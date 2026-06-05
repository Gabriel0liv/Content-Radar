from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal, Any, Dict

class SearchConfigBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: Literal["active", "paused", "archived"] = "active"
    language: Optional[str] = "pt"
    country_code: Optional[str] = "BR"
    region_code: Optional[str] = None
    days_back: Optional[int] = 5
    min_views: Optional[int] = 30000
    max_results_per_query: Optional[int] = 50
    sources_json: List[str] = Field(default_factory=lambda: ["youtube", "google_news"])
    keywords_json: List[str]
    negative_keywords_json: List[str] = Field(default_factory=list)
    youtube_categories_json: List[str] = Field(default_factory=list)

class SearchConfigCreate(SearchConfigBase):
    pass

class SearchConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
    language: Optional[str] = None
    country_code: Optional[str] = None
    region_code: Optional[str] = None
    days_back: Optional[int] = None
    min_views: Optional[int] = None
    max_results_per_query: Optional[int] = None
    sources_json: Optional[List[str]] = None
    keywords_json: Optional[List[str]] = None
    negative_keywords_json: Optional[List[str]] = None
    youtube_categories_json: Optional[List[str]] = None

class SearchConfigRead(SearchConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SearchConfigListResponse(BaseModel):
    configs: List[SearchConfigRead]
    total: int

class SearchRunRead(BaseModel):
    id: int
    search_config_id: int
    status: Literal["queued", "running", "completed", "failed"]
    trigger_source: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    items_found: int
    items_inserted: int
    items_updated: int
    error_message: Optional[str] = None
    raw_summary_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SearchRunCompletePayload(BaseModel):
    items_found: Optional[int] = 0
    items_inserted: Optional[int] = 0
    items_updated: Optional[int] = 0
    raw_summary_json: Optional[Dict[str, Any]] = None

class SearchRunFailPayload(BaseModel):
    error_message: str
    raw_summary_json: Optional[Dict[str, Any]] = None
