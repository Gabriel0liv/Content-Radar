from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from src.case_radar.providers.base import ProviderPermanentError, ProviderRateLimited, ProviderUnavailable
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SocialContextRecord, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url


_URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)


def _extract_links(text: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for raw in _URL_RE.findall(text or ""):
        cleaned = raw.rstrip(".,;:!?)]}'\"")
        if not cleaned:
            continue
        try:
            normalized = canonicalize_url(cleaned)
        except Exception:
            normalized = cleaned
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


class RedditCaseRadarProvider:
    name = "reddit-public"
    platform = "reddit"
    method = "public_http"

    def __init__(self, *, client: Any | None = None, user_agent: str | None = None, max_results: int = 25) -> None:
        self.client = client
        self.user_agent = user_agent or os.getenv("CASE_RADAR_REDDIT_USER_AGENT", "ContentRadar/1.0")
        self.max_results = max(1, min(100, int(max_results)))
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=True,
            comments_supported=True,
            replies_supported=True,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=False,
            official_api=False,
            cost_class="free",
        )

    def is_available(self) -> bool:
        return True

    def _client(self):
        return self.client or httpx.Client(timeout=20.0, headers={"User-Agent": self.user_agent})

    @staticmethod
    def _check_response(response: Any) -> None:
        status = int(getattr(response, "status_code", 200))
        if status == 429:
            raise ProviderRateLimited("Reddit rate limit atingido")
        if status >= 400:
            raise ProviderPermanentError(f"Reddit HTTP {status}")

    @staticmethod
    def _timestamp(value: Any) -> datetime | None:
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _post_to_candidate(data: dict[str, Any], discovery_query: str) -> Candidate:
        permalink = data.get("permalink") or ""
        url = f"https://reddit.com{permalink}" if permalink.startswith("/") else (permalink or data.get("url") or "")
        external_url = data.get("url_overridden_by_dest") or data.get("url")
        relation = {"external_url": external_url} if external_url and external_url != url else None
        return Candidate(
            platform="reddit",
            external_id=str(data.get("id")) if data.get("id") is not None else None,
            canonical_url=canonicalize_url(url),
            author_handle=None if data.get("author") in {None, "[deleted]"} else str(data.get("author")),
            author_display_name=None,
            title_or_caption=data.get("title"),
            text=None if data.get("selftext") in {None, "[deleted]", "[removed]"} else data.get("selftext"),
            published_at=RedditCaseRadarProvider._timestamp(data.get("created_utc")),
            media_type="video" if data.get("is_video") else "post",
            thumbnail_url=data.get("thumbnail") if str(data.get("thumbnail", "")).startswith("http") else None,
            duration_seconds=None,
            language=None,
            engagement={
                "score": int(data.get("score") or 0),
                "comments": int(data.get("num_comments") or 0),
            },
            hashtags=[],
            relation=relation,
            discovery_query=discovery_query,
            discovery_method="public_http",
            raw_json={
                "subreddit": data.get("subreddit"),
                "permalink": permalink,
                "is_video": bool(data.get("is_video")),
            },
            source_confidence=0.85,
        )

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        params = {"q": query_text, "limit": self.max_results, "sort": "relevance", "raw_json": 1}
        if cursor:
            params["after"] = cursor
        client = self._client()
        close_after = self.client is None
        try:
            response = client.get("https://www.reddit.com/search.json", params=params)
            self._check_response(response)
            payload = response.json()
        except (ProviderRateLimited, ProviderPermanentError):
            raise
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("Reddit indisponível") from exc
        finally:
            if close_after:
                client.close()
        children = ((payload.get("data") or {}).get("children") or []) if isinstance(payload, dict) else []
        candidates = [
            self._post_to_candidate(child.get("data") or {}, query_text)
            for child in children
            if child.get("kind") == "t3" and (child.get("data") or {}).get("id")
        ]
        return CandidatePage(
            candidates=candidates,
            next_cursor=(payload.get("data") or {}).get("after"),
            raw_json={"result_count": len(candidates)},
        )

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        client = self._client()
        close_after = self.client is None
        try:
            response = client.get(f"{candidate.canonical_url}.json", params={"raw_json": 1, "limit": 1})
            self._check_response(response)
            payload = response.json()
        finally:
            if close_after:
                client.close()
        try:
            post = payload[0]["data"]["children"][0]["data"]
        except (TypeError, KeyError, IndexError) as exc:
            raise ProviderPermanentError("Resposta de post do Reddit inválida") from exc
        enriched = self._post_to_candidate(post, candidate.discovery_query)
        return SourceSnapshot(candidate=enriched, raw_json={"source": "reddit_public_json"})

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        candidate = source.candidate if isinstance(source, SourceSnapshot) else source
        max_comments = int(getattr(options, "max_comments", None) or (options.get("max_comments") if isinstance(options, dict) else 100) or 100)
        max_depth = int(getattr(options, "max_depth", None) or (options.get("max_depth") if isinstance(options, dict) else 6) or 6)
        client = self._client()
        close_after = self.client is None
        try:
            response = client.get(f"{candidate.canonical_url}.json", params={"raw_json": 1, "limit": max_comments})
            self._check_response(response)
            payload = response.json()
        finally:
            if close_after:
                client.close()
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
                permalink = data.get("permalink")
                body_text = str(body)
                links = _extract_links(body_text)
                explicit_link = data.get("link_url")
                if explicit_link:
                    try:
                        normalized_link = canonicalize_url(str(explicit_link))
                    except Exception:
                        normalized_link = str(explicit_link)
                    if normalized_link not in links:
                        links.append(normalized_link)
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
                if isinstance(replies, dict):
                    walk(((replies.get("data") or {}).get("children") or []), depth + 1)

        walk(roots, 0)
        return SocialContextPage(items=items, raw_json={"collected": len(items)})
