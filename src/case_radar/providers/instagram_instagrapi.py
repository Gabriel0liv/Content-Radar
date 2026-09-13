from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from src.case_radar.url_normalization import canonicalize_url


_URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)


def _links(text: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in _URL_RE.findall(text or ""):
        raw = raw.rstrip(".,;:!?)]}'\"")
        if not raw:
            continue
        try:
            value = canonicalize_url(raw)
        except Exception:
            value = raw
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _media_url(media: Any) -> str:
    code = str(getattr(media, "code", "") or "")
    product_type = str(getattr(media, "product_type", "") or "")
    if product_type == "clips":
        return f"https://www.instagram.com/reel/{code}/"
    return f"https://www.instagram.com/p/{code}/"


def _media_to_row(media: Any) -> dict[str, Any]:
    user = getattr(media, "user", None)
    username = getattr(user, "username", None) if user else None
    full_name = getattr(user, "full_name", None) if user else None
    caption = str(getattr(media, "caption_text", "") or "")
    product_type = str(getattr(media, "product_type", "") or "")
    media_type = "video" if int(getattr(media, "media_type", 0) or 0) == 2 else "image"
    if product_type == "clips":
        media_type = "video"
    return {
        "id": str(getattr(media, "pk", "") or getattr(media, "id", "") or ""),
        "url": _media_url(media),
        "author_handle": f"@{username}" if username else None,
        "author_display_name": full_name,
        "caption": caption,
        "published_at": getattr(media, "taken_at", None),
        "media_type": media_type,
        "thumbnail_url": str(getattr(media, "thumbnail_url", "") or "") or None,
        "duration_seconds": float(getattr(media, "video_duration", 0) or 0) or None,
        "engagement": {
            "likes": max(0, int(getattr(media, "like_count", 0) or 0)),
            "comments": max(0, int(getattr(media, "comment_count", 0) or 0)),
            "views": max(0, int(getattr(media, "view_count", 0) or getattr(media, "play_count", 0) or 0)),
        },
        "raw_media_pk": str(getattr(media, "pk", "") or ""),
        "source_confidence": 0.85,
    }


class InstagrapiResearchAdapter:
    def __init__(self, client: Any, *, search_amount: int = 30) -> None:
        self.client = client
        self.search_amount = max(1, min(100, int(search_amount)))

    def search(self, query: str, cursor: str | None = None):
        # media_search handles its own pagination; the generic provider applies the run budget.
        medias = self.client.media_search(query, amount=self.search_amount)
        return [_media_to_row(media) for media in medias]

    def _media_from_url(self, url: str):
        pk = self.client.media_pk_from_url(url)
        return self.client.media_info(pk)

    def fetch_source(self, url: str, **kwargs):
        media = self._media_from_url(url)
        return _media_to_row(media)

    @staticmethod
    def _comment_row(comment: Any, *, parent_id: str | None = None, depth: int = 0, source_author: str | None = None) -> dict[str, Any]:
        user = getattr(comment, "user", None)
        username = getattr(user, "username", None) if user else None
        body = str(getattr(comment, "text", "") or "")
        comment_id = str(getattr(comment, "pk", "") or "")
        replied_to = getattr(comment, "replied_to_comment_id", None)
        return {
            "id": comment_id or None,
            "parent_id": str(replied_to or parent_id) if (replied_to or parent_id) else None,
            "depth": depth,
            "author_handle": f"@{username}" if username else None,
            "author_display_name": getattr(user, "full_name", None) if user else None,
            "body": body,
            "published_at": getattr(comment, "created_at_utc", None),
            "engagement": {"likes": max(0, int(getattr(comment, "like_count", 0) or 0))},
            "external_links": _links(body),
            "pinned": bool(getattr(comment, "is_pinned", False)),
            "author_reply": bool(username and source_author and username.casefold() == source_author.casefold()),
        }

    def fetch_social_context(self, url: str, **kwargs):
        max_comments = max(1, int(kwargs.get("max_comments") or 100))
        max_depth = max(0, int(kwargs.get("max_depth") or 0))
        media = self._media_from_url(url)
        media_pk = str(getattr(media, "pk", ""))
        media_id = str(getattr(media, "id", "") or media_pk)
        source_user = getattr(getattr(media, "user", None), "username", None)
        comments = list(self.client.media_comments(media_id, amount=max_comments))
        rows: list[dict[str, Any]] = []
        for comment in comments:
            if len(rows) >= max_comments:
                break
            row = self._comment_row(comment, source_author=source_user)
            rows.append(row)
            if max_depth <= 0:
                continue
            comment_id = row.get("id")
            if not comment_id:
                continue
            try:
                replies = self.client.media_comment_replies(media_id, comment_id, amount=max_comments - len(rows))
            except Exception:
                replies = []
            for reply in replies or []:
                if len(rows) >= max_comments:
                    break
                rows.append(
                    self._comment_row(
                        reply,
                        parent_id=comment_id,
                        depth=1,
                        source_author=source_user,
                    )
                )
        return rows


def create_adapter(session_file: str):
    try:
        from instagrapi import Client
    except ImportError as exc:
        raise ImportError("instagrapi não instalada") from exc

    path = Path(session_file)
    if not path.is_file():
        raise FileNotFoundError(session_file)

    client = Client()
    settings = client.load_settings(path)
    if settings:
        client.set_settings(settings)

    username = os.getenv("CASE_RADAR_INSTAGRAM_USERNAME", "").strip()
    password = os.getenv("CASE_RADAR_INSTAGRAM_PASSWORD", "").strip()
    if username and password:
        client.login(username, password)
    else:
        cookies = (settings or {}).get("cookies") or {}
        session_id = str(cookies.get("sessionid") or "").strip()
        if session_id:
            client.login_by_sessionid(session_id)

    return InstagrapiResearchAdapter(client)
