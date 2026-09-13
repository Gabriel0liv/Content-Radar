from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from src.case_radar.providers.base import ProviderAuthExpired, ProviderPermanentError, ProviderRateLimited, ProviderUnavailable
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SocialContextRecord, SourceSnapshot
from src.case_radar.url_normalization import canonicalize_url


_VIDEO_QUERY_URL = "https://open.tiktokapis.com/v2/research/video/query/"
_COMMENT_QUERY_URL = "https://open.tiktokapis.com/v2/research/video/comment/list/"
_VIDEO_FIELDS = (
    "id,video_description,create_time,region_code,share_count,view_count,like_count,"
    "comment_count,hashtag_names,username,voice_to_text,video_duration,favorites_count"
)
_COMMENT_FIELDS = "id,video_id,text,like_count,reply_count,parent_comment_id,create_time"


class TikTokResearchProvider:
    name = "tiktok-research-api"
    platform = "tiktok"
    method = "official_api"

    def __init__(self, access_token: str | None = None, *, client: Any | None = None, max_results: int = 100) -> None:
        self.access_token = (access_token if access_token is not None else os.getenv("TIKTOK_ACCESS_TOKEN", "")).strip()
        self.client = client
        self.max_results = max(1, min(100, int(max_results)))
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=False,
            comments_supported=True,
            replies_supported=True,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=bool(self.access_token),
            official_api=True,
            cost_class="metered",
        )

    def is_available(self) -> bool:
        return bool(self.access_token)

    def _client(self):
        return self.client or httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, url: str, *, fields: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.access_token:
            raise ProviderUnavailable("TikTok Research API sem token configurado", provider=self.name)
        client = self._client()
        close_after = self.client is None
        try:
            response = client.post(
                url,
                params={"fields": fields},
                json=payload,
                headers=self._headers(),
            )
            status = int(getattr(response, "status_code", 200))
            if status in {401, 403}:
                raise ProviderAuthExpired("TikTok Research API sem autorização ou escopo", provider=self.name)
            if status == 429:
                raise ProviderRateLimited("TikTok Research API rate limit atingido", provider=self.name)
            if status >= 400:
                raise ProviderPermanentError(f"TikTok Research API HTTP {status}", provider=self.name)
            data = response.json()
            error = data.get("error") if isinstance(data, dict) else None
            if isinstance(error, dict) and error.get("code") not in {None, "ok", "OK", 0, "0"}:
                message = str(error.get("message") or error.get("code") or "erro desconhecido")
                lowered = message.casefold()
                if "rate" in lowered or "limit" in lowered:
                    raise ProviderRateLimited("TikTok Research API rate limit atingido", provider=self.name)
                if "auth" in lowered or "scope" in lowered or "token" in lowered:
                    raise ProviderAuthExpired("TikTok Research API sem autorização ou escopo", provider=self.name)
                raise ProviderPermanentError(f"TikTok Research API: {message}", provider=self.name)
            return data if isinstance(data, dict) else {}
        except (ProviderAuthExpired, ProviderRateLimited, ProviderPermanentError):
            raise
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("TikTok Research API indisponível", provider=self.name) from exc
        finally:
            if close_after:
                client.close()

    @staticmethod
    def _date_window(request: Any) -> tuple[date, date, bool]:
        today = datetime.now(timezone.utc).date()
        requested_end = getattr(request, "date_to", None) or today
        requested_start = getattr(request, "date_from", None) or (requested_end - timedelta(days=29))
        truncated = (requested_end - requested_start).days > 29
        if truncated:
            requested_start = requested_end - timedelta(days=29)
        return requested_start, requested_end, truncated

    @staticmethod
    def _candidate(row: dict[str, Any], query_text: str) -> Candidate:
        video_id = str(row.get("id") or "")
        username = str(row.get("username") or "").lstrip("@")
        create_time = row.get("create_time")
        try:
            published_at = datetime.fromtimestamp(int(create_time), tz=timezone.utc) if create_time is not None else None
        except (TypeError, ValueError, OSError):
            published_at = None
        url = f"https://www.tiktok.com/@{username}/video/{video_id}" if username else f"https://www.tiktok.com/video/{video_id}"
        description = row.get("video_description") or None
        return Candidate(
            platform="tiktok",
            external_id=video_id or None,
            canonical_url=canonicalize_url(url),
            author_handle=f"@{username}" if username else None,
            author_display_name=None,
            title_or_caption=description,
            text=description,
            published_at=published_at,
            media_type="video",
            thumbnail_url=None,
            duration_seconds=float(row.get("video_duration") or 0) or None,
            language=None,
            engagement={
                "views": int(row.get("view_count") or 0),
                "likes": int(row.get("like_count") or 0),
                "comments": int(row.get("comment_count") or 0),
                "shares": int(row.get("share_count") or 0),
                "favorites": int(row.get("favorites_count") or 0),
            },
            hashtags=[str(value) for value in (row.get("hashtag_names") or [])],
            relation=None,
            discovery_query=query_text,
            discovery_method="official_api",
            raw_json={
                "region_code": row.get("region_code"),
                "voice_to_text": row.get("voice_to_text"),
            },
            source_confidence=0.95,
        )

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        start_date, end_date, truncated_window = self._date_window(request)
        cursor_value = 0
        search_id = None
        if cursor:
            try:
                cursor_value_text, search_id = cursor.split(":", 1)
                cursor_value = int(cursor_value_text)
            except (TypeError, ValueError):
                cursor_value = 0
                search_id = None
        payload: dict[str, Any] = {
            "query": {
                "and": [
                    {
                        "operation": "EQ",
                        "field_name": "keyword",
                        "field_values": [query_text],
                    }
                ]
            },
            "start_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
            "max_count": self.max_results,
            "cursor": cursor_value,
            "is_random": False,
        }
        if search_id:
            payload["search_id"] = search_id
        response = self._request(_VIDEO_QUERY_URL, fields=_VIDEO_FIELDS, payload=payload)
        data = response.get("data") or {}
        rows = data.get("videos") or []
        candidates = [self._candidate(row, query_text) for row in rows if isinstance(row, dict) and row.get("id")]
        next_cursor = None
        if data.get("has_more"):
            next_cursor = f"{int(data.get('cursor') or 0)}:{data.get('search_id') or ''}"
        return CandidatePage(
            candidates=candidates,
            next_cursor=next_cursor,
            raw_json={
                "result_count": len(candidates),
                "start_date": payload["start_date"],
                "end_date": payload["end_date"],
                "date_window_truncated_to_30_days": truncated_window,
            },
        )

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        return SourceSnapshot(candidate=candidate, raw_json={"source": "tiktok_research_api"})

    def _comment_page(self, *, video_id: str | None = None, comment_id: str | None = None, cursor: int = 0, max_count: int = 100) -> dict[str, Any]:
        payload: dict[str, Any] = {"max_count": max(1, min(100, max_count)), "cursor": max(0, cursor)}
        if comment_id:
            payload["comment_id"] = comment_id
        elif video_id:
            payload["video_id"] = video_id
        else:
            raise ValueError("video_id ou comment_id é obrigatório")
        return self._request(_COMMENT_QUERY_URL, fields=_COMMENT_FIELDS, payload=payload)

    @staticmethod
    def _social_record(row: dict[str, Any], *, depth: int = 0) -> SocialContextRecord:
        created = row.get("create_time")
        try:
            published_at = datetime.fromtimestamp(int(created), tz=timezone.utc) if created is not None else None
        except (TypeError, ValueError, OSError):
            published_at = None
        comment_id = str(row.get("id")) if row.get("id") is not None else None
        parent_id = str(row.get("parent_comment_id")) if row.get("parent_comment_id") else None
        return SocialContextRecord(
            platform_item_id=comment_id,
            parent_id=parent_id,
            depth=depth,
            author_handle=None,
            author_display_name=None,
            body=str(row.get("text") or ""),
            published_at=published_at,
            engagement={
                "likes": int(row.get("like_count") or 0),
                "replies": int(row.get("reply_count") or 0),
            },
            permalink=None,
            external_links=[],
            pinned=False,
            author_reply=False,
            raw_json={"video_id": row.get("video_id")},
        )

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        candidate = source.candidate if isinstance(source, SourceSnapshot) else source
        if not candidate.external_id:
            raise ProviderPermanentError("Vídeo TikTok sem id para comentários", provider=self.name)
        max_comments = int(getattr(options, "max_comments", None) or (options.get("max_comments") if isinstance(options, dict) else 100) or 100)
        max_depth = int(getattr(options, "max_depth", None) or (options.get("max_depth") if isinstance(options, dict) else 1) or 1)
        first = self._comment_page(video_id=candidate.external_id, max_count=min(100, max_comments))
        data = first.get("data") or {}
        rows = list(data.get("comments") or data.get("comment_list") or [])
        items: list[SocialContextRecord] = []
        parent_rows: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict) or len(items) >= max_comments:
                continue
            items.append(self._social_record(row, depth=0))
            parent_rows.append(row)
        if max_depth > 0:
            for row in parent_rows:
                if len(items) >= max_comments or int(row.get("reply_count") or 0) <= 0 or not row.get("id"):
                    continue
                replies_response = self._comment_page(
                    comment_id=str(row["id"]),
                    max_count=min(100, max_comments - len(items)),
                )
                replies_data = replies_response.get("data") or {}
                for reply in replies_data.get("comments") or replies_data.get("comment_list") or []:
                    if not isinstance(reply, dict) or len(items) >= max_comments:
                        break
                    items.append(self._social_record(reply, depth=1))
        return SocialContextPage(
            items=items,
            next_cursor=str(data.get("cursor")) if data.get("has_more") else None,
            raw_json={"collected": len(items), "official_research_api": True},
        )
