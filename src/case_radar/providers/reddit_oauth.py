from __future__ import annotations

import os
import time
from typing import Any

import httpx

from src.case_radar.providers.base import (
    ProviderAuthExpired,
    ProviderPermanentError,
    ProviderRateLimited,
    ProviderUnavailable,
)
from src.case_radar.providers.reddit import RedditCaseRadarProvider, _extract_links, _option_int
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SocialContextRecord, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url


class RedditOAuthProvider(RedditCaseRadarProvider):
    """Reddit application-only OAuth provider for read/search research.

    Uses the client_credentials grant and keeps the resulting bearer token only in
    memory. No user password or refresh token is required for signed-out reads.
    """

    name = "reddit-oauth"
    method = "official_api"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        *,
        user_agent: str | None = None,
        client: Any | None = None,
        max_results: int = 25,
    ) -> None:
        super().__init__(client=client, user_agent=user_agent, max_results=max_results)
        self.client_id = (client_id if client_id is not None else os.getenv("REDDIT_CLIENT_ID", "")).strip()
        self.client_secret = (client_secret if client_secret is not None else os.getenv("REDDIT_CLIENT_SECRET", "")).strip()
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=True,
            comments_supported=True,
            replies_supported=True,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=bool(self.client_id and self.client_secret),
            official_api=True,
            cost_class="free",
        )

    def is_available(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _oauth_client(self):
        return self.client or httpx.Client(timeout=20.0, headers={"User-Agent": self.user_agent})

    @staticmethod
    def _check_status(response: Any, *, auth_request: bool = False) -> None:
        status = int(getattr(response, "status_code", 200))
        if status in {401, 403}:
            if auth_request:
                raise ProviderAuthExpired("Credenciais OAuth do Reddit inválidas ou sem acesso")
            raise ProviderAuthExpired("Token OAuth do Reddit inválido, expirado ou sem escopo")
        if status == 429:
            raise ProviderRateLimited("Reddit OAuth rate limit atingido")
        if status >= 400:
            raise ProviderPermanentError(f"Reddit OAuth HTTP {status}")

    def _token(self) -> str:
        if not self.is_available():
            raise ProviderUnavailable("REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET não configurados", provider=self.name)
        now = time.monotonic()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        client = self._oauth_client()
        close_after = self.client is None
        try:
            response = client.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
                headers={"User-Agent": self.user_agent},
            )
            self._check_status(response, auth_request=True)
            payload = response.json()
        except (ProviderAuthExpired, ProviderRateLimited, ProviderPermanentError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable("Reddit OAuth token endpoint indisponível", provider=self.name) from exc
        finally:
            if close_after:
                client.close()

        token = str((payload or {}).get("access_token") or "").strip()
        if not token:
            raise ProviderAuthExpired("Reddit OAuth não retornou access token", provider=self.name)
        try:
            expires_in = max(60, int((payload or {}).get("expires_in") or 3600))
        except (TypeError, ValueError):
            expires_in = 3600
        self._access_token = token
        self._token_expires_at = now + max(30, expires_in - 60)
        return token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token()}",
            "User-Agent": self.user_agent,
        }

    @staticmethod
    def _as_official(candidate: Candidate) -> Candidate:
        return candidate.model_copy(update={"discovery_method": "official_api", "source_confidence": 0.9})

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        params: dict[str, Any] = {
            "q": query_text,
            "limit": self.max_results,
            "sort": "relevance",
            "raw_json": 1,
            "type": "link",
        }
        if cursor:
            params["after"] = cursor
        client = self._oauth_client()
        close_after = self.client is None
        try:
            response = client.get(
                "https://oauth.reddit.com/search",
                params=params,
                headers=self._headers(),
            )
            self._check_status(response)
            payload = response.json()
        except (ProviderAuthExpired, ProviderRateLimited, ProviderPermanentError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable("Reddit OAuth search indisponível", provider=self.name) from exc
        finally:
            if close_after:
                client.close()
        children = ((payload.get("data") or {}).get("children") or []) if isinstance(payload, dict) else []
        candidates = [
            self._as_official(self._post_to_candidate(child.get("data") or {}, query_text))
            for child in children
            if child.get("kind") == "t3" and (child.get("data") or {}).get("id")
        ]
        return CandidatePage(
            candidates=candidates,
            next_cursor=(payload.get("data") or {}).get("after") if isinstance(payload, dict) else None,
            raw_json={"result_count": len(candidates)},
        )

    def _thread(self, candidate: Candidate, *, limit: int) -> Any:
        if not candidate.external_id:
            raise ProviderPermanentError("Post Reddit sem id", provider=self.name)
        client = self._oauth_client()
        close_after = self.client is None
        try:
            response = client.get(
                f"https://oauth.reddit.com/comments/{candidate.external_id}.json",
                params={"raw_json": 1, "limit": limit},
                headers=self._headers(),
            )
            self._check_status(response)
            return response.json()
        except (ProviderAuthExpired, ProviderRateLimited, ProviderPermanentError):
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailable("Reddit OAuth comments indisponíveis", provider=self.name) from exc
        finally:
            if close_after:
                client.close()

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        payload = self._thread(candidate, limit=1)
        try:
            post = payload[0]["data"]["children"][0]["data"]
        except (TypeError, KeyError, IndexError) as exc:
            raise ProviderPermanentError("Resposta OAuth de post Reddit inválida", provider=self.name) from exc
        enriched = self._as_official(self._post_to_candidate(post, candidate.discovery_query))
        return SourceSnapshot(candidate=enriched, raw_json={"source": "reddit_oauth"})

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        candidate = source.candidate if isinstance(source, SourceSnapshot) else source
        max_comments = max(0, _option_int(options, "max_comments", 100))
        max_depth = max(0, _option_int(options, "max_depth", 6))
        payload = self._thread(candidate, limit=max_comments)
        try:
            roots = payload[1]["data"]["children"]
        except (TypeError, KeyError, IndexError):
            roots = []

        items: list[SocialContextRecord] = []

        def walk(children: list[dict[str, Any]], depth: int) -> None:
            if depth > max_depth or len(items) >= max_comments:
                return
            for child in children:
                if len(items) >= max_comments:
                    break
                if child.get("kind") != "t1":
                    continue
                data = child.get("data") or {}
                body = data.get("body")
                if body in {None, "[deleted]", "[removed]"}:
                    body = ""
                author = data.get("author")
                if author == "[deleted]":
                    author = None
                body_text = str(body)
                links = _extract_links(body_text)
                permalink = data.get("permalink")
                items.append(
                    SocialContextRecord(
                        platform_item_id=str(data.get("id")) if data.get("id") is not None else None,
                        parent_id=str(data.get("parent_id")) if data.get("parent_id") is not None else None,
                        depth=depth,
                        author_handle=author,
                        body=body_text,
                        published_at=self._timestamp(data.get("created_utc")),
                        engagement={"score": int(data.get("score") or 0)},
                        permalink=canonicalize_url(f"https://reddit.com{permalink}") if permalink else None,
                        external_links=links,
                        pinned=bool(data.get("stickied")),
                        author_reply=bool(author and candidate.author_handle and author == candidate.author_handle),
                        raw_json={"subreddit": data.get("subreddit")},
                    )
                )
                replies = data.get("replies")
                if depth < max_depth and isinstance(replies, dict):
                    walk(((replies.get("data") or {}).get("children") or []), depth + 1)

        walk(roots, 0)
        return SocialContextPage(items=items, raw_json={"collected": len(items), "source": "reddit_oauth"})
