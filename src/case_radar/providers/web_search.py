from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Protocol

import httpx

from src.case_radar.providers.base import ProviderPermanentError, ProviderUnavailable
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url, infer_platform_from_url


class SearchBackend(Protocol):
    def search(self, query: str, *, cursor: str | None = None, limit: int = 20) -> dict[str, Any]: ...


class HttpSearchBackend:
    def __init__(self, endpoint: str, api_key: str | None = None, timeout: float = 20.0) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key or ""
        self.timeout = timeout

    def search(self, query: str, *, cursor: str | None = None, limit: int = 20) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"query": query, "limit": limit}
        if cursor:
            payload["cursor"] = cursor
        try:
            response = httpx.post(self.endpoint, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderPermanentError(f"Web search HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("Backend de web search indisponível") from exc
        data = response.json()
        if not isinstance(data, dict):
            raise ProviderPermanentError("Resposta inválida do backend de web search")
        return data


class DDGSSearchBackend:
    """Free local metasearch backend. No API key is required."""

    def __init__(self, *, region: str | None = None, backend: str | None = None, timeout: int = 10) -> None:
        self.region = (region or os.getenv("CASE_RADAR_DDGS_REGION", "wt-wt")).strip() or "wt-wt"
        self.backend = (backend or os.getenv("CASE_RADAR_DDGS_BACKEND", "auto")).strip() or "auto"
        self.timeout = max(1, int(timeout))

    def search(self, query: str, *, cursor: str | None = None, limit: int = 20) -> dict[str, Any]:
        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise ProviderUnavailable("Backend gratuito DDGS não instalado") from exc
        try:
            page = max(1, int(cursor or "1"))
        except ValueError:
            page = 1
        try:
            rows = DDGS(timeout=self.timeout).text(
                query,
                region=self.region,
                safesearch="moderate",
                max_results=max(1, min(50, int(limit))),
                page=page,
                backend=self.backend,
            )
        except Exception as exc:
            raise ProviderUnavailable("Busca web gratuita temporariamente indisponível") from exc
        results = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            url = row.get("href") or row.get("url")
            if not url:
                continue
            results.append(
                {
                    "url": str(url),
                    "title": row.get("title"),
                    "snippet": row.get("body") or row.get("snippet"),
                    "source_confidence": 0.45,
                }
            )
        next_cursor = str(page + 1) if len(results) >= max(1, min(50, int(limit))) else None
        return {
            "results": results,
            "next_cursor": next_cursor,
            "backend": "ddgs",
        }


class WebSearchProvider:
    name = "web-search"
    method = "web_search"

    def __init__(
        self,
        *,
        backend: SearchBackend | None = None,
        target_platform: str = "web",
        site_domain: str | None = None,
        result_limit: int = 20,
        allow_free_backend: bool = True,
    ) -> None:
        self.platform = target_platform
        self.site_domain = site_domain
        self.result_limit = result_limit
        if backend is None:
            endpoint = os.getenv("CASE_RADAR_WEB_SEARCH_URL", "").strip()
            api_key = os.getenv("CASE_RADAR_WEB_SEARCH_API_KEY", "").strip()
            if endpoint:
                backend = HttpSearchBackend(endpoint, api_key)
            elif allow_free_backend:
                backend = DDGSSearchBackend()
        self.backend = backend
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=False,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=False,
            historical_search_supported=True,
            authenticated=False,
            official_api=False,
            cost_class="free",
        )

    def is_available(self) -> bool:
        return self.backend is not None

    def _query_text(self, query: Any) -> str:
        value = getattr(query, "query_text", query)
        text = " ".join(str(value).split())
        if self.site_domain:
            return f"site:{self.site_domain} {text}"
        return text

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        if self.backend is None:
            raise ProviderUnavailable("Nenhum backend de web search disponível", provider=self.name)
        query_text = self._query_text(query)
        data = self.backend.search(query_text, cursor=cursor, limit=self.result_limit)
        rows = data.get("results") or []
        candidates: list[Candidate] = []
        for row in rows:
            if not isinstance(row, dict) or not row.get("url"):
                continue
            canonical_url = canonicalize_url(str(row["url"]))
            inferred = infer_platform_from_url(canonical_url)
            platform = self.platform if self.platform != "web" else inferred
            candidates.append(
                Candidate(
                    platform=platform,
                    external_id=str(row.get("id")) if row.get("id") is not None else None,
                    canonical_url=canonical_url,
                    author_handle=row.get("author_handle"),
                    author_display_name=row.get("author_display_name"),
                    title_or_caption=row.get("title"),
                    text=row.get("snippet") or row.get("text"),
                    published_at=self._parse_datetime(row.get("published_at")),
                    media_type=row.get("media_type"),
                    thumbnail_url=row.get("thumbnail_url"),
                    duration_seconds=row.get("duration_seconds"),
                    language=row.get("language"),
                    engagement=row.get("engagement") or {},
                    hashtags=row.get("hashtags") or [],
                    relation=row.get("relation"),
                    discovery_query=query_text,
                    discovery_method="web_search",
                    raw_json={key: value for key, value in row.items() if key not in {"api_key", "token", "authorization"}},
                    source_confidence=float(row.get("source_confidence", 0.45)),
                )
            )
        return CandidatePage(
            candidates=candidates,
            next_cursor=data.get("next_cursor"),
            raw_json={"result_count": len(candidates), "backend": data.get("backend")},
        )

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        raise ProviderUnavailable("Web search não oferece fetch_source direto", provider=self.name)

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        raise ProviderUnavailable("Web search não oferece contexto social direto", provider=self.name)
