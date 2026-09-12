from __future__ import annotations

import os
from datetime import date, datetime, time, timezone
from typing import Any, Callable

from src.case_radar.providers.base import ProviderPermanentError, ProviderRateLimited, ProviderUnavailable
from src.case_radar.types import Candidate, CandidatePage, ProviderCapabilities, SocialContextPage, SourceSnapshot
from src.youtube_collector import _duration_to_seconds, _youtube_client


class YouTubeCaseRadarProvider:
    name = "youtube-official"
    platform = "youtube"
    method = "official_api"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        client_factory: Callable[[str], Any] = _youtube_client,
        max_results: int = 25,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("YOUTUBE_API_KEY", "")).strip()
        self.client_factory = client_factory
        self.max_results = max(1, min(50, int(max_results)))
        self.capabilities = ProviderCapabilities(
            search_supported=True,
            source_fetch_supported=True,
            comments_supported=False,
            replies_supported=False,
            quote_posts_supported=False,
            media_metadata_supported=True,
            historical_search_supported=True,
            authenticated=bool(self.api_key),
            official_api=True,
            cost_class="metered",
        )

    def is_available(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _iso_date(value: date | None, *, end: bool = False) -> str | None:
        if value is None:
            return None
        dt = datetime.combine(value, time.max if end else time.min, tzinfo=timezone.utc)
        return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _map_error(exc: Exception):
        text = str(exc).casefold()
        if "quota" in text or "rate limit" in text or "403" in text or "429" in text:
            raise ProviderRateLimited("Quota/rate limit da YouTube Data API") from exc
        raise ProviderPermanentError(f"Falha na YouTube Data API: {exc}") from exc

    def _client(self):
        if not self.api_key:
            raise ProviderUnavailable("YOUTUBE_API_KEY não configurada", provider=self.name)
        return self.client_factory(self.api_key)

    def _details_to_candidate(self, item: dict[str, Any], discovery_query: str) -> Candidate:
        snippet = item.get("snippet") or {}
        statistics = item.get("statistics") or {}
        details = item.get("contentDetails") or {}
        video_id = str(item.get("id") or "").strip()
        thumbnails = snippet.get("thumbnails") or {}
        thumbnail = (thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}).get("url")
        engagement = {}
        for source_key, target_key in (("viewCount", "views"), ("likeCount", "likes"), ("commentCount", "comments")):
            try:
                engagement[target_key] = int(statistics.get(source_key, 0))
            except (TypeError, ValueError):
                engagement[target_key] = 0
        return Candidate(
            platform="youtube",
            external_id=video_id or None,
            canonical_url=f"https://youtube.com/watch?v={video_id}",
            author_handle=None,
            author_display_name=snippet.get("channelTitle"),
            title_or_caption=snippet.get("title"),
            text=snippet.get("description"),
            published_at=self._parse_datetime(snippet.get("publishedAt")),
            media_type="video",
            thumbnail_url=thumbnail,
            duration_seconds=float(_duration_to_seconds(details.get("duration", ""))) or None,
            language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
            engagement=engagement,
            hashtags=[str(tag) for tag in (snippet.get("tags") or [])],
            relation=None,
            discovery_query=discovery_query,
            discovery_method="official_api",
            raw_json={
                "id": video_id,
                "channel_id": snippet.get("channelId"),
                "category_id": snippet.get("categoryId"),
            },
            source_confidence=0.9,
        )

    def search(self, request: Any, query: Any, cursor: str | None = None) -> CandidatePage:
        youtube = self._client()
        query_text = " ".join(str(getattr(query, "query_text", query)).split())
        params: dict[str, Any] = {
            "part": "id,snippet",
            "q": query_text,
            "type": "video",
            "order": "relevance",
            "maxResults": self.max_results,
        }
        language = getattr(query, "language", None)
        if language and len(str(language)) <= 5:
            params["relevanceLanguage"] = str(language).split("-")[0]
        date_from = getattr(request, "date_from", None)
        date_to = getattr(request, "date_to", None)
        if date_from:
            params["publishedAfter"] = self._iso_date(date_from)
        if date_to:
            params["publishedBefore"] = self._iso_date(date_to, end=True)
        if cursor:
            params["pageToken"] = cursor

        try:
            search_response = youtube.search().list(**params).execute()
            video_ids = [
                item.get("id", {}).get("videoId")
                for item in search_response.get("items", [])
                if item.get("id", {}).get("videoId")
            ]
            if not video_ids:
                return CandidatePage(candidates=[], next_cursor=search_response.get("nextPageToken"))
            details_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids),
                maxResults=len(video_ids),
            ).execute()
        except Exception as exc:
            self._map_error(exc)

        candidates = [self._details_to_candidate(item, query_text) for item in details_response.get("items", [])]
        return CandidatePage(
            candidates=candidates,
            next_cursor=search_response.get("nextPageToken"),
            raw_json={"result_count": len(candidates)},
        )

    def fetch_source(self, candidate: Candidate) -> SourceSnapshot:
        if not candidate.external_id:
            raise ProviderPermanentError("Candidate do YouTube sem video id", provider=self.name)
        youtube = self._client()
        try:
            response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=candidate.external_id,
                maxResults=1,
            ).execute()
        except Exception as exc:
            self._map_error(exc)
        items = response.get("items", [])
        if not items:
            raise ProviderPermanentError("Vídeo do YouTube não encontrado", provider=self.name)
        enriched = self._details_to_candidate(items[0], candidate.discovery_query)
        return SourceSnapshot(candidate=enriched, raw_json={"source": "youtube_data_api"})

    def fetch_social_context(self, source: Candidate | SourceSnapshot, options: Any) -> SocialContextPage:
        raise ProviderUnavailable("Comentários do YouTube não habilitados no adapter inicial", provider=self.name)
