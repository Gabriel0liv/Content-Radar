from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.case_radar.types import Platform, ResearchDepth


ProviderBudget = Annotated[int, Field(ge=0, le=5000)]
CaseStatus = Literal["researching", "ready", "approved", "rejected", "duplicate", "already_used"]
RunStatus = Literal["queued", "running", "completed", "partially_completed", "failed", "cancelled"]


class CaseResearchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str = Field(min_length=1, max_length=500)
    desired_usable_cases: int = Field(default=10, ge=1, le=50)
    languages: list[str] = Field(default_factory=lambda: ["pt", "en", "es"])
    platforms: list[Platform] = Field(
        default_factory=lambda: ["youtube", "x", "tiktok", "instagram", "reddit", "web"]
    )
    date_from: date | None = None
    date_to: date | None = None
    include_terms: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    research_depth: ResearchDepth = "balanced"
    provider_budgets: dict[Platform, ProviderBudget] = Field(default_factory=dict)
    global_result_budget: int = Field(default=500, ge=1, le=5000)

    @field_validator("theme")
    @classmethod
    def normalize_theme(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("theme não pode ser vazio")
        return normalized

    @field_validator("languages", "platforms")
    @classmethod
    def require_non_empty_list(cls, value: list):
        if not value:
            raise ValueError("a lista não pode ser vazia")
        return value

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            normalized = item.strip().lower()
            if not normalized:
                continue
            if normalized not in seen:
                seen.add(normalized)
                result.append(normalized)
        if not result:
            raise ValueError("languages deve conter ao menos um idioma válido")
        return result

    @field_validator("include_terms", "exclude_terms", "priorities", "exclusions")
    @classmethod
    def normalize_string_lists(cls, value: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            normalized = " ".join(item.split())
            if not normalized:
                continue
            key = normalized.casefold()
            if key not in seen:
                seen.add(key)
                result.append(normalized)
        return result

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.date_from is not None and self.date_to is not None and self.date_from > self.date_to:
            raise ValueError("date_from não pode ser posterior a date_to")
        return self


class CaseResearchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RunStatus
    stage: str
    progress_percent: int
    progress_message: str | None = None
    request_json: dict[str, Any]
    provider_coverage_json: dict[str, Any]
    discovered_candidates: int
    clustered_cases: int
    usable_cases: int
    rejected_cases: int
    worker_id: str | None = None
    errors_json: list[dict[str, Any]]
    result_summary_json: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    updated_at: datetime


class CaseResearchRunListResponse(BaseModel):
    items: list[CaseResearchRunRead]
    total: int
    limit: int
    offset: int


class CaseResearchQueryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    language: str
    target_platform: str | None = None
    query_text: str
    intent: str
    status: str
    result_count: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ResearchSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    query_id: int | None = None
    platform: Platform
    external_id: str | None = None
    canonical_url: str
    author_handle: str | None = None
    author_display_name: str | None = None
    title_or_caption: str | None = None
    text: str | None = None
    published_at: datetime | None = None
    discovered_at: datetime
    media_type: str | None = None
    thumbnail_url: str | None = None
    duration_seconds: float | None = None
    language: str | None = None
    engagement_json: dict[str, Any]
    hashtags_json: list[str]
    relation_json: dict[str, Any] | None = None
    discovery_method: str
    source_confidence: float
    content_item_id: int | None = None
    reference_source_id: int | None = None


class ResearchCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    provisional_title: str
    normalized_summary: str | None = None
    status: CaseStatus
    alleged_date: datetime | None = None
    alleged_location: str | None = None
    earliest_known_date: datetime | None = None
    origin_status: Literal["unknown", "likely", "confirmed"]
    origin_confidence: float
    research_confidence: float
    likely_original_source_id: int | None = None
    earliest_known_source_id: int | None = None
    selected_primary_source_id: int | None = None
    dossier_version: int
    dossier_json: dict[str, Any] | None = None
    manual_notes: str | None = None
    already_used: bool
    created_at: datetime
    updated_at: datetime


class ResearchCasePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CaseStatus | None = None
    manual_notes: str | None = None
    already_used: bool | None = None
    selected_primary_source_id: int | None = Field(default=None, ge=1)
