from typing import List
from datetime import datetime, timezone

import isodate
from googleapiclient.discovery import build


def _parse_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _duration_to_seconds(duration: str) -> int:
    try:
        parsed = isodate.parse_duration(duration)
        return int(parsed.total_seconds())
    except Exception:
        return 0


def _youtube_client(api_key: str):
    return build("youtube", "v3", developerKey=api_key)


def search_recent_short_videos(
    api_key: str,
    keyword: str,
    niche: str,
    published_after: datetime,
    region_code: str = "BR",
    max_results: int = 25,
) -> List[dict]:
    youtube = _youtube_client(api_key)

    published_after_iso = (
        published_after.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    search_response = (
        youtube.search()
        .list(
            part="id,snippet",
            q=keyword,
            type="video",
            order="viewCount",
            videoDuration="short",
            publishedAfter=published_after_iso,
            regionCode=region_code,
            relevanceLanguage="pt",
            maxResults=max_results,
        )
        .execute()
    )

    video_ids = [
        item["id"]["videoId"]
        for item in search_response.get("items", [])
        if item.get("id", {}).get("videoId")
    ]

    if not video_ids:
        return []

    videos_response = (
        youtube.videos()
        .list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
            maxResults=len(video_ids),
        )
        .execute()
    )

    results = []

    for item in videos_response.get("items", []):
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        details = item.get("contentDetails", {})

        video_id = item["id"]
        duration_seconds = _duration_to_seconds(details.get("duration", ""))

        # Shorts atuais podem ter até 3 minutos. A API "short" ainda pode retornar vídeos até 4 min.
        if duration_seconds > 180:
            continue

        results.append(
            {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId", ""),
                "default_language": snippet.get("defaultLanguage", ""),
                "default_audio_language": snippet.get("defaultAudioLanguage", ""),
                "channel_id": snippet.get("channelId", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "published_at": snippet.get("publishedAt", ""),
                "views": _parse_int(stats.get("viewCount")),
                "likes": _parse_int(stats.get("likeCount")),
                "comments": _parse_int(stats.get("commentCount")),
                "duration_seconds": duration_seconds,
                "url": f"https://www.youtube.com/shorts/{video_id}",
                "keyword": keyword,
                "niche": niche,
            }
        )

    return results
