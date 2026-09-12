from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.case_radar.types import (
    Candidate,
    CandidatePage,
    Platform,
    ProviderCapabilities,
    SocialContextPage,
    SourceSnapshot,
)


class ProviderError(RuntimeError):
    code = "provider_error"

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message)
        self.provider = provider

    def as_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": str(self), "provider": self.provider}


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"


class ProviderAuthExpired(ProviderError):
    code = "provider_auth_expired"


class ProviderRateLimited(ProviderError):
    code = "provider_rate_limited"


class ProviderPermanentError(ProviderError):
    code = "provider_permanent_error"


@dataclass
class ProviderBudget:
    request_limit: int
    result_limit: int
    cost_unit_limit: int = 0
    requests_used: int = 0
    results_used: int = 0
    cost_units_used: int = 0

    def can_consume(self, *, requests: int = 0, results: int = 0, cost_units: int = 0) -> bool:
        if self.request_limit >= 0 and self.requests_used + requests > self.request_limit:
            return False
        if self.result_limit >= 0 and self.results_used + results > self.result_limit:
            return False
        if self.cost_unit_limit > 0 and self.cost_units_used + cost_units > self.cost_unit_limit:
            return False
        return True

    def consume(self, *, requests: int = 0, results: int = 0, cost_units: int = 0) -> None:
        if not self.can_consume(requests=requests, results=results, cost_units=cost_units):
            raise ProviderUnavailable("Budget do provider esgotado")
        self.requests_used += requests
        self.results_used += results
        self.cost_units_used += cost_units

    @property
    def exhausted(self) -> bool:
        requests_exhausted = self.request_limit >= 0 and self.requests_used >= self.request_limit
        results_exhausted = self.result_limit >= 0 and self.results_used >= self.result_limit
        cost_exhausted = self.cost_unit_limit > 0 and self.cost_units_used >= self.cost_unit_limit
        return requests_exhausted or results_exhausted or cost_exhausted


class CaseRadarProvider(Protocol):
    name: str
    platform: Platform
    method: str
    capabilities: ProviderCapabilities

    def is_available(self) -> bool: ...

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage: ...

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot: ...

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage: ...
