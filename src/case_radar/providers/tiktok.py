from __future__ import annotations

import importlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from src.case_radar.providers.base import ProviderAuthExpired, ProviderPermanentError, ProviderRateLimited, ProviderUnavailable
from src.case_radar.providers.web_search import WebSearchProvider
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SocialContextRecord, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class TikTokWebSearchProvider(WebSearchProvider):
    name = "tiktok-web-search"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(target_platform="tiktok", site_domain="tiktok.com", **kwargs)
        self.method = "web_search"


class TikTokOfficialProvider:
    name = "tiktok-official"
    platform = "tiktok"
    method = "official_api"

    def __init__(self, access_token: str | None = None, *, endpoint: str | None = None, client: Any | None = None) -> None:
        self.access_token = (access_token if access_token is not None else os.getenv("TIKTOK_ACCESS_TOKEN", "")).strip()
        self.endpoint = (endpoint if endpoint is not None else os.getenv("CASE_RADAR_TIKTOK_OFFICIAL_SEARCH_URL", "")).strip()
        self.client = client
        search_enabled = bool(self.access_token and self.endpoint)
        self.capabilities = ProviderCapabilities(
            search_supported=search_enabled,
            source_fetch_supported=False,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=search_enabled,
            authenticated=bool(self.access_token),
            official_api=True,
            cost_class="metered",
        )

    def is_available(self) -> bool:
        return self.capabilities.search_supported

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        if not self.is_available():
            raise ProviderUnavailable("TikTok official/research search não configurado", provider=self.name)
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        payload = {"query": query_text, "cursor": cursor}
        client = self.client or httpx.Client(timeout=20.0)
        close_after = self.client is None
        try:
            response = client.post(
                self.endpoint,
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            status = int(getattr(response, "status_code", 200))
            if status in {401, 403}:
                raise ProviderAuthExpired("Credencial TikTok inválida ou sem escopo", provider=self.name)
            if status == 429:
                raise ProviderRateLimited("TikTok rate limit atingido", provider=self.name)
            if status >= 400:
                raise ProviderPermanentError(f"TikTok API HTTP {status}", provider=self.name)
            data = response.json()
        finally:
            if close_after:
                client.close()
        candidates = []
        for row in data.get("results") or []:
            if not isinstance(row, dict) or not row.get("url"):
                continue
            candidates.append(
                Candidate(
                    platform="tiktok",
                    external_id=str(row.get("id")) if row.get("id") is not None else None,
                    canonical_url=canonicalize_url(str(row["url"])),
                    author_handle=row.get("author_handle"),
                    author_display_name=row.get("author_display_name"),
                    title_or_caption=row.get("title") or row.get("caption"),
                    text=row.get("caption") or row.get("text"),
                    media_type="video",
                    thumbnail_url=row.get("thumbnail_url"),
                    duration_seconds=row.get("duration_seconds"),
                    language=row.get("language"),
                    engagement=row.get("engagement") or {},
                    hashtags=row.get("hashtags") or [],
                    relation=row.get("relation"),
                    discovery_query=query_text,
                    discovery_method="official_api",
                    raw_json={"official": True},
                    source_confidence=float(row.get("source_confidence", 0.9)),
                )
            )
        return CandidatePage(candidates=candidates, next_cursor=data.get("next_cursor"), raw_json={"result_count": len(candidates)})

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        raise ProviderUnavailable("TikTok official fetch_source não configurado", provider=self.name)

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        raise ProviderUnavailable("TikTok official comments não configurados", provider=self.name)


class TikTokLoggedInProvider:
    name = "tiktok-logged-in"
    platform = "tiktok"
    method = "logged_in"

    def __init__(self, session_file: str | None = None, *, adapter: Any | None = None) -> None:
        self.session_file = (session_file if session_file is not None else os.getenv("CASE_RADAR_TIKTOK_SESSION_FILE", "")).strip()
        self.adapter = adapter
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=False,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=True,
            official_api=False,
            cost_class="free",
        )
        if adapter is not None:
            self._refresh_capabilities(adapter)

    def _refresh_capabilities(self, adapter: Any) -> None:
        self.capabilities.source_fetch_supported = callable(getattr(adapter, "fetch_source", None))
        social_supported = callable(getattr(adapter, "fetch_social_context", None))
        self.capabilities.comments_supported = social_supported
        self.capabilities.replies_supported = social_supported

    def _load_adapter(self):
        if self.adapter is not None:
            self._refresh_capabilities(self.adapter)
            return self.adapter
        if not self.session_file or not Path(self.session_file).is_file():
            raise ProviderUnavailable("Sessão TikTok não configurada", provider=self.name)
        module_name = os.getenv("CASE_RADAR_TIKTOK_ADAPTER_MODULE", "").strip()
        if not module_name:
            raise ProviderUnavailable("Adapter TikTok logged-in não configurado", provider=self.name)
        try:
            module = importlib.import_module(module_name)
            self.adapter = module.create_adapter(self.session_file)
            self._refresh_capabilities(self.adapter)
            return self.adapter
        except ImportError as exc:
            raise ProviderUnavailable("Adapter TikTok logged-in não instalado", provider=self.name) from exc
        except Exception as exc:
            raise ProviderAuthExpired("Sessão TikTok inválida ou expirada", provider=self.name) from exc

    def is_available(self) -> bool:
        if self.adapter is not None:
            self._refresh_capabilities(self.adapter)
            return True
        if not (self.session_file and Path(self.session_file).is_file() and os.getenv("CASE_RADAR_TIKTOK_ADAPTER_MODULE", "").strip()):
            return False
        try:
            self._load_adapter()
            return True
        except (ProviderUnavailable, ProviderAuthExpired):
            return False

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        adapter = self._load_adapter()
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        try:
            rows = adapter.search(query_text, cursor=cursor)
        except Exception as exc:
            text = str(exc).casefold()
            if any(token in text for token in ("login", "auth", "challenge", "cookie", "session")):
                raise ProviderAuthExpired("Sessão TikTok inválida, expirada ou em challenge", provider=self.name) from exc
            if "429" in text or "rate" in text:
                raise ProviderRateLimited("TikTok logged-in rate limit atingido", provider=self.name) from exc
            raise ProviderUnavailable("TikTok logged-in indisponível", provider=self.name) from exc
        candidates = []
        for row in rows or []:
            if not row.get("url"):
                continue
            candidates.append(
                Candidate(
                    platform="tiktok",
                    external_id=str(row.get("id")) if row.get("id") is not None else None,
                    canonical_url=canonicalize_url(str(row["url"])),
                    author_handle=row.get("author_handle"),
                    author_display_name=row.get("author_display_name"),
                    title_or_caption=row.get("caption"),
                    text=row.get("caption"),
                    media_type="video",
                    thumbnail_url=row.get("thumbnail_url"),
                    duration_seconds=row.get("duration_seconds"),
                    language=row.get("language"),
                    engagement=row.get("engagement") or {},
                    hashtags=row.get("hashtags") or [],
                    relation=row.get("relation"),
                    discovery_query=query_text,
                    discovery_method="logged_in",
                    raw_json={},
                    source_confidence=float(row.get("source_confidence", 0.7)),
                )
            )
        return CandidatePage(candidates=candidates, next_cursor=None, raw_json={"result_count": len(candidates)})

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        adapter = self._load_adapter()
        method = getattr(adapter, "fetch_source", None)
        if not callable(method):
            raise ProviderUnavailable("TikTok logged-in fetch_source não suportado pelo adapter", provider=self.name)
        try:
            row = method(candidate.canonical_url, external_id=candidate.external_id)
        except Exception as exc:
            raise ProviderUnavailable("TikTok logged-in falhou ao enriquecer a fonte", provider=self.name) from exc
        if isinstance(row, Candidate):
            enriched = row
        elif isinstance(row, dict):
            enriched = Candidate(
                platform="tiktok",
                external_id=str(row.get("id") or candidate.external_id) if (row.get("id") or candidate.external_id) else None,
                canonical_url=canonicalize_url(str(row.get("url") or candidate.canonical_url)),
                author_handle=row.get("author_handle") or candidate.author_handle,
                author_display_name=row.get("author_display_name") or candidate.author_display_name,
                title_or_caption=row.get("caption") or candidate.title_or_caption,
                text=row.get("caption") or row.get("text") or candidate.text,
                published_at=_parse_datetime(row.get("published_at")) or candidate.published_at,
                media_type="video",
                thumbnail_url=row.get("thumbnail_url") or candidate.thumbnail_url,
                duration_seconds=row.get("duration_seconds") or candidate.duration_seconds,
                language=row.get("language") or candidate.language,
                engagement=row.get("engagement") or candidate.engagement,
                hashtags=row.get("hashtags") or candidate.hashtags,
                relation=row.get("relation") or candidate.relation,
                discovery_query=candidate.discovery_query,
                discovery_method="logged_in",
                raw_json={},
                source_confidence=float(row.get("source_confidence", candidate.source_confidence)),
            )
        else:
            raise ProviderUnavailable("Adapter TikTok retornou fonte em formato inválido", provider=self.name)
        return SourceSnapshot(candidate=enriched, raw_json={"source": "tiktok_logged_in"})

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        adapter = self._load_adapter()
        method = getattr(adapter, "fetch_social_context", None)
        if not callable(method):
            raise ProviderUnavailable("TikTok logged-in comments não suportados pelo adapter", provider=self.name)
        candidate = source.candidate if isinstance(source, SourceSnapshot) else source
        max_comments = int(getattr(options, "max_comments", None) or (options.get("max_comments") if isinstance(options, dict) else 100) or 100)
        max_depth = int(getattr(options, "max_depth", None) or (options.get("max_depth") if isinstance(options, dict) else 6) or 6)
        try:
            rows = method(candidate.canonical_url, external_id=candidate.external_id, max_comments=max_comments, max_depth=max_depth)
        except Exception as exc:
            text = str(exc).casefold()
            if any(token in text for token in ("login", "auth", "challenge", "cookie", "session")):
                raise ProviderAuthExpired("Sessão TikTok inválida, expirada ou em challenge", provider=self.name) from exc
            raise ProviderUnavailable("TikTok logged-in falhou ao coletar comentários", provider=self.name) from exc
        items: list[SocialContextRecord] = []
        for row in list(rows or [])[:max_comments]:
            if not isinstance(row, dict):
                continue
            items.append(
                SocialContextRecord(
                    platform_item_id=str(row.get("id")) if row.get("id") is not None else None,
                    parent_id=str(row.get("parent_id")) if row.get("parent_id") is not None else None,
                    depth=max(0, int(row.get("depth") or 0)),
                    author_handle=row.get("author_handle"),
                    author_display_name=row.get("author_display_name"),
                    body=str(row.get("body") or row.get("text") or ""),
                    published_at=_parse_datetime(row.get("published_at")),
                    engagement=row.get("engagement") or {},
                    permalink=canonicalize_url(str(row["permalink"])) if row.get("permalink") else None,
                    external_links=[canonicalize_url(str(url)) for url in (row.get("external_links") or [])],
                    pinned=bool(row.get("pinned")),
                    author_reply=bool(row.get("author_reply")),
                    raw_json={},
                )
            )
        return SocialContextPage(items=items, raw_json={"collected": len(items), "adapter": True})
