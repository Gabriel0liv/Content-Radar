from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

from src.case_radar.providers.base import ProviderAuthExpired, ProviderRateLimited, ProviderUnavailable
from src.case_radar.providers.web_search import WebSearchProvider
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url


class InstagramWebSearchProvider(WebSearchProvider):
    name = "instagram-web-search"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(target_platform="instagram", site_domain="instagram.com", **kwargs)
        self.method = "web_search"


class InstagramOfficialProvider:
    name = "instagram-official"
    platform = "instagram"
    method = "official_api"

    def __init__(self, access_token: str | None = None) -> None:
        self.access_token = (access_token if access_token is not None else os.getenv("INSTAGRAM_ACCESS_TOKEN", "")).strip()
        self.capabilities = ProviderCapabilities(
            search_supported=False,
            source_fetch_supported=False,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=False,
            historical_search_supported=False,
            authenticated=bool(self.access_token),
            official_api=True,
            cost_class="metered",
        )

    def is_available(self) -> bool:
        return False

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        raise ProviderUnavailable(
            "Instagram official não oferece busca global de Reels neste adapter",
            provider=self.name,
        )

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        raise ProviderUnavailable("Instagram official fetch_source não suportado neste adapter", provider=self.name)

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        raise ProviderUnavailable("Instagram official comments não suportados neste adapter", provider=self.name)


class InstagramLoggedInProvider:
    name = "instagram-logged-in"
    platform = "instagram"
    method = "logged_in"

    def __init__(self, session_file: str | None = None, *, adapter: Any | None = None) -> None:
        self.session_file = (session_file if session_file is not None else os.getenv("CASE_RADAR_INSTAGRAM_SESSION_FILE", "")).strip()
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

    def _load_adapter(self):
        if self.adapter is not None:
            return self.adapter
        if not self.session_file or not Path(self.session_file).is_file():
            raise ProviderUnavailable("Sessão Instagram não configurada", provider=self.name)
        module_name = os.getenv("CASE_RADAR_INSTAGRAM_ADAPTER_MODULE", "").strip()
        if not module_name:
            raise ProviderUnavailable("Adapter Instagram logged-in não configurado", provider=self.name)
        try:
            module = importlib.import_module(module_name)
            return module.create_adapter(self.session_file)
        except ImportError as exc:
            raise ProviderUnavailable("Adapter Instagram logged-in não instalado", provider=self.name) from exc
        except Exception as exc:
            raise ProviderAuthExpired("Sessão Instagram inválida ou expirada", provider=self.name) from exc

    def is_available(self) -> bool:
        if self.adapter is not None:
            return True
        return bool(self.session_file and Path(self.session_file).is_file() and os.getenv("CASE_RADAR_INSTAGRAM_ADAPTER_MODULE", "").strip())

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        adapter = self._load_adapter()
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        try:
            rows = adapter.search(query_text, cursor=cursor)
        except Exception as exc:
            text = str(exc).casefold()
            if any(token in text for token in ("login", "auth", "challenge", "cookie", "session")):
                raise ProviderAuthExpired("Sessão Instagram inválida, expirada ou em challenge", provider=self.name) from exc
            if "429" in text or "rate" in text:
                raise ProviderRateLimited("Instagram logged-in rate limit atingido", provider=self.name) from exc
            raise ProviderUnavailable("Instagram logged-in indisponível", provider=self.name) from exc
        candidates = []
        for row in rows or []:
            if not row.get("url"):
                continue
            candidates.append(
                Candidate(
                    platform="instagram",
                    external_id=str(row.get("id")) if row.get("id") is not None else None,
                    canonical_url=canonicalize_url(str(row["url"])),
                    author_handle=row.get("author_handle"),
                    author_display_name=row.get("author_display_name"),
                    title_or_caption=row.get("caption"),
                    text=row.get("caption"),
                    media_type=row.get("media_type") or "video",
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
        raise ProviderUnavailable("Instagram logged-in fetch_source ainda não suportado", provider=self.name)

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        raise ProviderUnavailable("Instagram logged-in comments ainda não suportados", provider=self.name)
