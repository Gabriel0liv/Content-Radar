from __future__ import annotations

import asyncio
import importlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from src.case_radar.providers.base import (
    ProviderAuthExpired,
    ProviderPermanentError,
    ProviderRateLimited,
    ProviderUnavailable,
)
from src.case_radar.providers.web_search import WebSearchProvider
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SocialContextRecord, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url


def _safe_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class XWebSearchProvider(WebSearchProvider):
    name = "x-web-search"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(target_platform="x", site_domain="x.com", **kwargs)
        self.method = "web_search"


class XOfficialApiProvider:
    name = "x-official-api"
    platform = "x"
    method = "official_api"

    def __init__(self, bearer_token: str | None = None, *, client: Any | None = None, max_results: int = 25) -> None:
        self.bearer_token = (bearer_token if bearer_token is not None else os.getenv("X_BEARER_TOKEN", "")).strip()
        self.client = client
        self.max_results = max(10, min(100, int(max_results)))
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=True,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=False,
            authenticated=bool(self.bearer_token),
            official_api=True,
            cost_class="paid",
        )

    def is_available(self) -> bool:
        return bool(self.bearer_token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.bearer_token}"}

    def _client(self):
        return self.client or httpx.Client(timeout=20.0)

    @staticmethod
    def _check(response: Any) -> None:
        status = int(getattr(response, "status_code", 200))
        if status in {401, 403}:
            raise ProviderAuthExpired("Credencial da X API inválida ou sem acesso")
        if status == 429:
            raise ProviderRateLimited("X API rate limit atingido")
        if status >= 400:
            raise ProviderPermanentError(f"X API HTTP {status}")

    @staticmethod
    def _tweet_to_candidate(tweet: dict[str, Any], query_text: str) -> Candidate:
        tweet_id = str(tweet.get("id") or "")
        metrics = tweet.get("public_metrics") or {}
        author_id = tweet.get("author_id")
        return Candidate(
            platform="x",
            external_id=tweet_id or None,
            canonical_url=f"https://x.com/i/status/{tweet_id}",
            author_handle=None,
            author_display_name=None,
            title_or_caption=None,
            text=tweet.get("text"),
            published_at=_safe_datetime(tweet.get("created_at")),
            media_type="post",
            thumbnail_url=None,
            duration_seconds=None,
            language=tweet.get("lang"),
            engagement={
                "likes": int(metrics.get("like_count") or 0),
                "replies": int(metrics.get("reply_count") or 0),
                "reposts": int(metrics.get("retweet_count") or 0),
                "quotes": int(metrics.get("quote_count") or 0),
            },
            hashtags=[],
            relation={"author_id": author_id} if author_id else None,
            discovery_query=query_text,
            discovery_method="official_api",
            raw_json={"conversation_id": tweet.get("conversation_id")},
            source_confidence=0.9,
        )

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        if not self.bearer_token:
            raise ProviderUnavailable("X_BEARER_TOKEN não configurado", provider=self.name)
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        params = {
            "query": query_text,
            "max_results": self.max_results,
            "tweet.fields": "id,text,author_id,created_at,lang,public_metrics,conversation_id",
        }
        if cursor:
            params["next_token"] = cursor
        client = self._client()
        close_after = self.client is None
        try:
            response = client.get(
                "https://api.x.com/2/tweets/search/recent",
                params=params,
                headers=self._headers(),
            )
            self._check(response)
            payload = response.json()
        except (ProviderAuthExpired, ProviderRateLimited, ProviderPermanentError):
            raise
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("X API indisponível") from exc
        finally:
            if close_after:
                client.close()
        candidates = [self._tweet_to_candidate(tweet, query_text) for tweet in payload.get("data") or []]
        return CandidatePage(
            candidates=candidates,
            next_cursor=(payload.get("meta") or {}).get("next_token"),
            raw_json={"result_count": len(candidates)},
        )

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        if not candidate.external_id:
            raise ProviderPermanentError("Post da X sem id", provider=self.name)
        if not self.bearer_token:
            raise ProviderUnavailable("X_BEARER_TOKEN não configurado", provider=self.name)
        client = self._client()
        close_after = self.client is None
        try:
            response = client.get(
                f"https://api.x.com/2/tweets/{candidate.external_id}",
                params={"tweet.fields": "id,text,author_id,created_at,lang,public_metrics,conversation_id"},
                headers=self._headers(),
            )
            self._check(response)
            payload = response.json()
        finally:
            if close_after:
                client.close()
        tweet = payload.get("data")
        if not isinstance(tweet, dict):
            raise ProviderPermanentError("Post da X não encontrado", provider=self.name)
        return SourceSnapshot(
            candidate=self._tweet_to_candidate(tweet, candidate.discovery_query),
            raw_json={"source": "x_official_api"},
        )

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        raise ProviderUnavailable("Replies/quotes não habilitados neste adapter oficial", provider=self.name)


class XLoggedInProvider:
    name = "x-logged-in"
    platform = "x"
    method = "logged_in"

    def __init__(self, session_file: str | None = None, *, client: Any | None = None) -> None:
        self.session_file = (session_file if session_file is not None else os.getenv("CASE_RADAR_X_SESSION_FILE", "")).strip()
        self.client = client
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=True,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=True,
            official_api=False,
            cost_class="free",
        )
        if client is not None:
            self._refresh_social_capabilities(client)

    @staticmethod
    def _social_method(client: Any):
        for method_name in ("fetch_social_context", "get_tweet_replies", "get_replies"):
            method = getattr(client, method_name, None)
            if callable(method):
                return method_name, method
        return None, None

    def _refresh_social_capabilities(self, client: Any) -> None:
        method_name, _ = self._social_method(client)
        supported = method_name is not None
        self.capabilities.comments_supported = supported
        self.capabilities.replies_supported = supported

    def _session_exists(self) -> bool:
        return bool(self.session_file and Path(self.session_file).is_file())

    def is_available(self) -> bool:
        if self.client is not None:
            self._refresh_social_capabilities(self.client)
            return True
        if not self._session_exists():
            return False
        try:
            importlib.import_module("twikit")
            return True
        except ImportError:
            return False

    def _load_client(self):
        if self.client is not None:
            self._refresh_social_capabilities(self.client)
            return self.client
        if not self._session_exists():
            raise ProviderUnavailable("Sessão X não configurada", provider=self.name)
        try:
            twikit = importlib.import_module("twikit")
            client = twikit.Client(language="en-US")
            client.load_cookies(self.session_file)
            self.client = client
            self._refresh_social_capabilities(client)
            return client
        except ImportError as exc:
            raise ProviderUnavailable("Adapter X logged-in não instalado", provider=self.name) from exc
        except Exception as exc:
            raise ProviderAuthExpired("Sessão X inválida ou expirada", provider=self.name) from exc

    @staticmethod
    def _object_to_candidate(tweet: Any, query_text: str) -> Candidate:
        tweet_id = str(getattr(tweet, "id", "") or "")
        user = getattr(tweet, "user", None)
        username = getattr(user, "screen_name", None) or getattr(user, "name", None)
        return Candidate(
            platform="x",
            external_id=tweet_id or None,
            canonical_url=canonicalize_url(f"https://x.com/{username or 'i'}/status/{tweet_id}"),
            author_handle=f"@{username}" if username else None,
            author_display_name=getattr(user, "name", None) if user else None,
            text=getattr(tweet, "text", None) or getattr(tweet, "full_text", None),
            published_at=_safe_datetime(getattr(tweet, "created_at", None)),
            media_type="post",
            language=getattr(tweet, "lang", None),
            engagement={
                "likes": int(getattr(tweet, "favorite_count", 0) or 0),
                "replies": int(getattr(tweet, "reply_count", 0) or 0),
                "reposts": int(getattr(tweet, "retweet_count", 0) or 0),
            },
            discovery_query=query_text,
            discovery_method="logged_in",
            raw_json={},
            source_confidence=0.75,
        )

    @staticmethod
    def _run_awaitable(value: Any):
        if not hasattr(value, "__await__"):
            return value
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(value)
        raise ProviderPermanentError("X logged-in não pode abrir event loop dentro de event loop ativo")

    @staticmethod
    def _social_record_from_any(item: Any, depth: int = 0) -> SocialContextRecord:
        if isinstance(item, dict):
            get = item.get
            user = get("user") or {}
            user_name = user.get("screen_name") if isinstance(user, dict) else None
        else:
            get = lambda key, default=None: getattr(item, key, default)
            user = get("user")
            user_name = getattr(user, "screen_name", None) if user else None
        external_links = get("external_links") or []
        if not external_links:
            urls = get("urls") or []
            external_links = [str(url) for url in urls]
        parent_id = get("in_reply_to_status_id") or get("parent_id")
        item_id = get("id")
        engagement = get("engagement") or {
            "likes": int(get("favorite_count", 0) or 0),
            "replies": int(get("reply_count", 0) or 0),
            "reposts": int(get("retweet_count", 0) or 0),
        }
        return SocialContextRecord(
            platform_item_id=str(item_id) if item_id is not None else None,
            parent_id=str(parent_id) if parent_id is not None else None,
            depth=max(0, int(get("depth", depth) or depth)),
            author_handle=(f"@{user_name}" if user_name else get("author_handle")),
            author_display_name=get("author_display_name") or (getattr(user, "name", None) if user and not isinstance(user, dict) else None),
            body=str(get("text") or get("full_text") or get("body") or ""),
            published_at=_safe_datetime(get("created_at") or get("published_at")),
            engagement=engagement,
            permalink=canonicalize_url(str(get("permalink"))) if get("permalink") else None,
            external_links=[canonicalize_url(str(url)) for url in external_links],
            pinned=bool(get("pinned", False)),
            author_reply=bool(get("author_reply", False)),
            raw_json={},
        )

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        client = self._load_client()
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        try:
            result = self._run_awaitable(client.search_tweet(query_text, "Latest"))
        except ProviderPermanentError:
            raise
        except Exception as exc:
            text = str(exc).casefold()
            if "login" in text or "auth" in text or "challenge" in text or "cookie" in text:
                raise ProviderAuthExpired("Sessão X inválida, expirada ou em challenge", provider=self.name) from exc
            if "rate" in text or "429" in text:
                raise ProviderRateLimited("X logged-in rate limit atingido", provider=self.name) from exc
            raise ProviderUnavailable("X logged-in indisponível", provider=self.name) from exc
        tweets = list(result or [])
        candidates = [self._object_to_candidate(tweet, query_text) for tweet in tweets]
        return CandidatePage(candidates=candidates, next_cursor=None, raw_json={"result_count": len(candidates)})

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        client = self._load_client()
        if not candidate.external_id:
            raise ProviderPermanentError("Post da X sem id", provider=self.name)
        try:
            tweet = self._run_awaitable(client.get_tweet_by_id(candidate.external_id))
        except Exception as exc:
            raise ProviderUnavailable("Falha ao buscar post X pela sessão", provider=self.name) from exc
        return SourceSnapshot(candidate=self._object_to_candidate(tweet, candidate.discovery_query), raw_json={"source": "x_logged_in"})

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        client = self._load_client()
        method_name, method = self._social_method(client)
        if method is None:
            raise ProviderUnavailable("Coleta de replies X não suportada pelo client instalado", provider=self.name)
        candidate = source.candidate if isinstance(source, SourceSnapshot) else source
        if not candidate.external_id:
            raise ProviderPermanentError("Post da X sem id para coletar replies", provider=self.name)
        max_comments = int(getattr(options, "max_comments", None) or (options.get("max_comments") if isinstance(options, dict) else 100) or 100)
        max_depth = int(getattr(options, "max_depth", None) or (options.get("max_depth") if isinstance(options, dict) else 6) or 6)
        try:
            if method_name == "fetch_social_context":
                value = method(candidate.canonical_url, external_id=candidate.external_id, max_comments=max_comments, max_depth=max_depth)
            else:
                value = method(candidate.external_id)
            result = self._run_awaitable(value)
        except Exception as exc:
            text = str(exc).casefold()
            if any(token in text for token in ("login", "auth", "challenge", "cookie", "session")):
                raise ProviderAuthExpired("Sessão X inválida, expirada ou em challenge", provider=self.name) from exc
            if "429" in text or "rate" in text:
                raise ProviderRateLimited("X logged-in rate limit atingido", provider=self.name) from exc
            raise ProviderUnavailable("Falha ao coletar replies da X", provider=self.name) from exc
        rows = list(result or [])[:max_comments]
        items = [self._social_record_from_any(row) for row in rows]
        return SocialContextPage(items=items, raw_json={"collected": len(items), "method": method_name})
