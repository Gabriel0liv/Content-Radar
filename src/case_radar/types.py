from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Platform = Literal["youtube", "x", "tiktok", "instagram", "reddit", "web"]
ResearchDepth = Literal["quick", "balanced", "deep"]
CostClass = Literal["free", "metered", "paid"]


class ProviderCapabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search_supported: bool
    source_fetch_supported: bool
    comments_supported: bool
    replies_supported: bool
    quote_posts_supported: bool
    media_metadata_supported: bool
    historical_search_supported: bool
    authenticated: bool
    official_api: bool
    cost_class: CostClass


class Candidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Platform
    external_id: str | None = None
    canonical_url: str = Field(min_length=1)
    author_handle: str | None = None
    author_display_name: str | None = None
    title_or_caption: str | None = None
    text: str | None = None
    published_at: datetime | None = None
    media_type: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    language: str | None = None
    engagement: dict[str, int] = Field(default_factory=dict)
    hashtags: list[str] = Field(default_factory=list)
    relation: dict[str, Any] | None = None
    discovery_query: str = Field(min_length=1)
    discovery_method: str = Field(min_length=1)
    raw_json: dict[str, Any] = Field(default_factory=dict)
    source_confidence: float = Field(ge=0, le=1)


class CandidatePage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: list[Candidate] = Field(default_factory=list)
    next_cursor: str | None = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class SourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: Candidate
    raw_json: dict[str, Any] = Field(default_factory=dict)


class SocialContextRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform_item_id: str | None = None
    parent_id: str | None = None
    depth: int = Field(default=0, ge=0)
    author_handle: str | None = None
    author_display_name: str | None = None
    body: str
    published_at: datetime | None = None
    engagement: dict[str, int] = Field(default_factory=dict)
    permalink: str | None = None
    external_links: list[str] = Field(default_factory=list)
    pinned: bool = False
    author_reply: bool = False
    raw_json: dict[str, Any] = Field(default_factory=dict)


class SocialContextPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SocialContextRecord] = Field(default_factory=list)
    next_cursor: str | None = None
    raw_json: dict[str, Any] = Field(default_factory=dict)
