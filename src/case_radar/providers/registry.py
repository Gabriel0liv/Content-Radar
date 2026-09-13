from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.case_radar.providers.base import (
    CaseRadarProvider,
    ProviderAuthExpired,
    ProviderBudget,
    ProviderError,
    ProviderPermanentError,
    ProviderRateLimited,
    ProviderUnavailable,
)
from src.case_radar.types import CandidatePage, Platform


@dataclass
class ProviderSearchOutcome:
    page: CandidatePage | None
    provider_name: str | None
    errors: list[dict[str, str | None]] = field(default_factory=list)


class ProviderRegistry:
    def __init__(self, priorities: dict[Platform, list[str]] | None = None) -> None:
        self._providers: dict[tuple[Platform, str], CaseRadarProvider] = {}
        self._priorities = priorities or {}

    def register(self, provider: CaseRadarProvider) -> None:
        self._providers[(provider.platform, provider.method)] = provider

    def get(self, platform: Platform, method: str) -> CaseRadarProvider | None:
        return self._providers.get((platform, method))

    def methods_for(self, platform: Platform) -> list[str]:
        if platform in self._priorities:
            return list(self._priorities[platform])
        return [method for provider_platform, method in self._providers if provider_platform == platform]

    def available_providers(self, platform: Platform) -> list[CaseRadarProvider]:
        providers: list[CaseRadarProvider] = []
        for method in self.methods_for(platform):
            provider = self.get(platform, method)
            if provider is None:
                continue
            if not provider.capabilities.search_supported:
                continue
            try:
                available = provider.is_available()
            except Exception:
                available = False
            if available:
                providers.append(provider)
        return providers

    @staticmethod
    def _record_error(errors: list[dict[str, str | None]], provider: CaseRadarProvider, exc: ProviderError) -> None:
        if exc.provider is None:
            exc.provider = provider.name
        errors.append(exc.as_dict())

    def _search_provider_pages(
        self,
        provider: CaseRadarProvider,
        request: Any,
        query: Any,
        budget: ProviderBudget,
        cursor: str | None,
        errors: list[dict[str, str | None]],
    ) -> CandidatePage:
        candidates = []
        current_cursor = cursor
        seen_cursors: set[str] = set()
        page_metadata: list[dict[str, Any]] = []
        truncated = False

        while not budget.exhausted:
            if not budget.can_consume(requests=1):
                break
            budget.consume(requests=1)
            try:
                page = provider.search(request, query, cursor=current_cursor)
            except (ProviderUnavailable, ProviderAuthExpired, ProviderRateLimited, ProviderPermanentError, ProviderError) as exc:
                if candidates:
                    self._record_error(errors, provider, exc)
                    break
                raise

            remaining = max(0, budget.result_limit - budget.results_used)
            accepted = page.candidates[:remaining]
            candidates.extend(accepted)
            budget.consume(results=len(accepted))
            page_metadata.append(dict(page.raw_json or {}))
            if len(accepted) < len(page.candidates):
                truncated = True
                current_cursor = None
                break

            next_cursor = page.next_cursor
            if not next_cursor or budget.exhausted:
                current_cursor = next_cursor
                break
            if next_cursor in seen_cursors or next_cursor == current_cursor:
                errors.append(
                    ProviderPermanentError(
                        "Provider retornou cursor repetido; paginação interrompida",
                        provider=provider.name,
                    ).as_dict()
                )
                current_cursor = None
                break
            seen_cursors.add(next_cursor)
            current_cursor = next_cursor

        raw_json: dict[str, Any] = {
            "result_count": len(candidates),
            "pages_fetched": len(page_metadata),
            "pages": page_metadata,
        }
        if truncated or budget.exhausted:
            raw_json["truncated_by_budget"] = True
        return CandidatePage(candidates=candidates, next_cursor=current_cursor, raw_json=raw_json)

    def search_with_fallback(
        self,
        platform: Platform,
        request: Any,
        query: Any,
        budget: ProviderBudget,
        cursor: str | None = None,
    ) -> ProviderSearchOutcome:
        errors: list[dict[str, str | None]] = []
        attempted = False

        for method in self.methods_for(platform):
            provider = self.get(platform, method)
            if provider is None or not provider.capabilities.search_supported:
                continue
            attempted = True

            if budget.exhausted:
                errors.append(
                    ProviderUnavailable(
                        "Budget do provider esgotado",
                        provider=provider.name,
                    ).as_dict()
                )
                break

            try:
                if not provider.is_available():
                    raise ProviderUnavailable("Provider indisponível", provider=provider.name)
                page = self._search_provider_pages(provider, request, query, budget, cursor, errors)
                return ProviderSearchOutcome(page=page, provider_name=provider.name, errors=errors)
            except (ProviderUnavailable, ProviderAuthExpired, ProviderRateLimited) as exc:
                self._record_error(errors, provider, exc)
                continue
            except ProviderPermanentError as exc:
                self._record_error(errors, provider, exc)
                continue
            except ProviderError as exc:
                self._record_error(errors, provider, exc)
                continue

        if not attempted:
            errors.append(ProviderUnavailable(f"Nenhum provider registrado para {platform}").as_dict())
        return ProviderSearchOutcome(page=None, provider_name=None, errors=errors)


def build_default_registry() -> ProviderRegistry:
    from src.case_radar.providers.instagram import (
        InstagramLoggedInProvider,
        InstagramOfficialProvider,
        InstagramWebSearchProvider,
    )
    from src.case_radar.providers.reddit import RedditCaseRadarProvider
    from src.case_radar.providers.reddit_oauth import RedditOAuthProvider
    from src.case_radar.providers.tiktok import TikTokLoggedInProvider, TikTokWebSearchProvider
    from src.case_radar.providers.tiktok_research import TikTokResearchProvider
    from src.case_radar.providers.web_search import WebSearchProvider
    from src.case_radar.providers.x import XOfficialApiProvider, XWebSearchProvider
    from src.case_radar.providers.x_twikit import TwikitXLoggedInProvider
    from src.case_radar.providers.youtube import YouTubeCaseRadarProvider

    registry = ProviderRegistry(
        priorities={
            "youtube": ["official_api", "web_search"],
            "x": ["logged_in", "web_search", "official_api"],
            "tiktok": ["logged_in", "web_search", "official_api"],
            "instagram": ["logged_in", "web_search", "official_api"],
            "reddit": ["official_api", "public_http", "web_search"],
            "web": ["web_search"],
        }
    )
    registry.register(YouTubeCaseRadarProvider())
    registry.register(WebSearchProvider(target_platform="youtube", site_domain="youtube.com"))
    registry.register(TwikitXLoggedInProvider())
    registry.register(XWebSearchProvider())
    registry.register(XOfficialApiProvider())
    registry.register(TikTokLoggedInProvider())
    registry.register(TikTokWebSearchProvider())
    registry.register(TikTokResearchProvider())
    registry.register(InstagramLoggedInProvider())
    registry.register(InstagramWebSearchProvider())
    registry.register(InstagramOfficialProvider())
    registry.register(RedditOAuthProvider())
    registry.register(RedditCaseRadarProvider())
    registry.register(WebSearchProvider(target_platform="reddit", site_domain="reddit.com"))
    registry.register(WebSearchProvider())
    return registry
