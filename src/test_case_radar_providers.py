from types import SimpleNamespace

from src.case_radar.providers.base import (
    ProviderAuthExpired,
    ProviderBudget,
    ProviderUnavailable,
)
from src.case_radar.providers.registry import ProviderRegistry
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities


class FakeProvider:
    def __init__(
        self,
        *,
        name,
        platform="x",
        method="web_search",
        available=True,
        error=None,
        candidates=None,
        search_supported=True,
    ):
        self.name = name
        self.platform = platform
        self.method = method
        self.available = available
        self.error = error
        self._candidates = candidates or []
        self.calls = 0
        self.capabilities = ProviderCapabilities(
            search_supported=search_supported,
            source_fetch_supported=True,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=False,
            official_api=False,
            cost_class="free",
        )

    def is_available(self):
        return self.available

    def search(self, request, query, cursor=None):
        self.calls += 1
        if self.error:
            raise self.error
        return CandidatePage(candidates=self._candidates)

    def fetch_source(self, candidate):
        raise NotImplementedError

    def fetch_social_context(self, source, options):
        raise NotImplementedError


def _candidate(external_id="1"):
    return Candidate(
        platform="x",
        external_id=external_id,
        canonical_url=f"https://x.com/user/status/{external_id}",
        discovery_query="strange forest video",
        discovery_method="web_search",
        source_confidence=0.5,
    )


def test_registry_skips_provider_without_search_capability():
    registry = ProviderRegistry(priorities={"x": ["no_search"]})
    provider = FakeProvider(name="x-no-search", method="no_search", search_supported=False)
    registry.register(provider)
    assert registry.available_providers("x") == []


def test_registry_falls_back_from_unavailable_a_to_b():
    registry = ProviderRegistry(priorities={"x": ["logged_in", "web_search"]})
    first = FakeProvider(name="x-logged", method="logged_in", available=False)
    second = FakeProvider(name="x-web", method="web_search", candidates=[_candidate()])
    registry.register(first)
    registry.register(second)

    outcome = registry.search_with_fallback(
        "x",
        SimpleNamespace(),
        SimpleNamespace(),
        ProviderBudget(request_limit=5, result_limit=10),
    )

    assert outcome.provider_name == "x-web"
    assert len(outcome.page.candidates) == 1
    assert outcome.errors[0]["code"] == "provider_unavailable"


def test_registry_falls_back_after_auth_expired():
    registry = ProviderRegistry(priorities={"x": ["logged_in", "web_search"]})
    first = FakeProvider(
        name="x-logged",
        method="logged_in",
        error=ProviderAuthExpired("sessão expirada"),
    )
    second = FakeProvider(name="x-web", method="web_search", candidates=[_candidate()])
    registry.register(first)
    registry.register(second)

    outcome = registry.search_with_fallback(
        "x",
        SimpleNamespace(),
        SimpleNamespace(),
        ProviderBudget(request_limit=5, result_limit=10),
    )

    assert outcome.provider_name == "x-web"
    assert outcome.errors[0]["code"] == "provider_auth_expired"


def test_provider_budget_prevents_unbounded_requests():
    budget = ProviderBudget(request_limit=1, result_limit=10)
    budget.consume(requests=1)
    assert budget.exhausted is True


def test_registry_truncates_results_to_remaining_budget():
    registry = ProviderRegistry(priorities={"x": ["web_search"]})
    provider = FakeProvider(
        name="x-web",
        method="web_search",
        candidates=[_candidate("1"), _candidate("2"), _candidate("3")],
    )
    registry.register(provider)
    budget = ProviderBudget(request_limit=2, result_limit=2)

    outcome = registry.search_with_fallback("x", SimpleNamespace(), SimpleNamespace(), budget)

    assert len(outcome.page.candidates) == 2
    assert outcome.page.raw_json["truncated_by_budget"] is True
    assert budget.results_used == 2


def test_registry_returns_partial_error_instead_of_raising_when_all_methods_fail():
    registry = ProviderRegistry(priorities={"x": ["logged_in"]})
    provider = FakeProvider(
        name="x-logged",
        method="logged_in",
        error=ProviderUnavailable("indisponível"),
    )
    registry.register(provider)

    outcome = registry.search_with_fallback(
        "x",
        SimpleNamespace(),
        SimpleNamespace(),
        ProviderBudget(request_limit=3, result_limit=10),
    )

    assert outcome.page is None
    assert outcome.provider_name is None
    assert outcome.errors[0]["code"] == "provider_unavailable"
