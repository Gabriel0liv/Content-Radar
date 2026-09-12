from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.case_radar.types import Platform, ResearchDepth


ProviderBudget = Annotated[int, Field(ge=0, le=5000)]


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
