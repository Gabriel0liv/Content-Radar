import re
from collections import defaultdict
from typing import Iterable, List

from sqlalchemy.orm import Session

from src.repositories.channel_profiles_repository import ChannelProfilesRepository
from src.repositories.topics_repository import TopicsRepository
from src.schemas.topics import TopicCreate
from src.services.youtube_metadata_service import normalize_tag


GENERIC_SERIES_TERMS = {
    "minecraft",
    "gaming",
    "game",
    "smp",
    "roleplay",
    "rp",
    "lore",
    "analog horror",
    "arg",
    "hardcore",
    "series",
    "challenge",
    "survival",
}
SERIES_MARKERS = {"smp", "series", "season", "roleplay", "rp", "archives", "chronicles", "saga"}


def _clean_name(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _is_specific_series_name(value: str, require_marker: bool) -> bool:
    cleaned = _clean_name(value)
    normalized = normalize_tag(cleaned)
    if not cleaned or normalized in GENERIC_SERIES_TERMS:
        return False
    if len(cleaned) < 4 or len(cleaned) > 80:
        return False
    words = normalized.split()
    if len(words) < 2:
        return False
    if require_marker and not any(marker in words for marker in SERIES_MARKERS):
        return False
    return True


def _item_candidates(item) -> List[dict]:
    candidates = []
    raw = getattr(item, "raw_json", None) or {}
    playlist_title = raw.get("playlist_title") or raw.get("playlist")
    if playlist_title and _is_specific_series_name(playlist_title, require_marker=False):
        candidates.append({"name": _clean_name(playlist_title), "source": "playlist"})

    for tag in getattr(item, "youtube_tags_json", None) or []:
        if _is_specific_series_name(str(tag), require_marker=True):
            candidates.append({"name": _clean_name(tag), "source": "tag"})

    title = _clean_name(getattr(item, "title", ""))
    for part in re.split(r"\s*[|•:]\s*", title):
        if _is_specific_series_name(part, require_marker=True):
            candidates.append({"name": _clean_name(part), "source": "title_pattern"})

    dedup = {}
    for candidate in candidates:
        key = normalize_tag(candidate["name"])
        entry = dedup.setdefault(key, {"name": candidate["name"], "sources": set()})
        entry["sources"].add(candidate["source"])
    return [
        {"name": entry["name"], "sources": sorted(entry["sources"])}
        for entry in dedup.values()
    ]


def select_series_candidates(items: Iterable, minimum_videos: int = 3) -> List[dict]:
    aggregated = defaultdict(lambda: {"name": None, "item_positions": set(), "item_ids": [], "sources": set()})
    for position, item in enumerate(items):
        for candidate in _item_candidates(item):
            key = normalize_tag(candidate["name"])
            entry = aggregated[key]
            entry["name"] = entry["name"] or candidate["name"]
            entry["item_positions"].add(position)
            item_id = getattr(item, "id", None)
            if item_id is not None and item_id not in entry["item_ids"]:
                entry["item_ids"].append(item_id)
            entry["sources"].update(candidate["sources"])

    results = []
    for entry in aggregated.values():
        video_count = len(entry["item_positions"])
        if video_count < minimum_videos:
            continue
        results.append(
            {
                "name": entry["name"],
                "video_count": video_count,
                "item_ids": entry["item_ids"],
                "sources": sorted(entry["sources"]),
            }
        )
    return sorted(results, key=lambda item: (-item["video_count"], item["name"].casefold()))


class SeriesDetectionService:
    def __init__(self, db: Session):
        self.db = db
        self.channel_repo = ChannelProfilesRepository(db)
        self.topics_repo = TopicsRepository(db)

    def detect_and_persist(self, channel_id: str, minimum_videos: int = 3) -> List[dict]:
        items = self.channel_repo.list_recent_content(channel_id, limit=50)
        candidates = select_series_candidates(items, minimum_videos=minimum_videos)
        by_id = {item.id: item for item in items}

        for candidate in candidates:
            topic = self.topics_repo.create_topic(TopicCreate(name=candidate["name"], type="series"))
            confidence = min(0.95, 0.68 + 0.07 * (candidate["video_count"] - minimum_videos))
            for item_id in candidate["item_ids"]:
                if item_id not in by_id:
                    continue
                existing = self.topics_repo.get_content_topic(item_id, topic.id)
                if existing is not None and existing.source == "manual":
                    continue
                self.topics_repo.upsert_content_topic(
                    content_item_id=item_id,
                    topic_id=topic.id,
                    confidence=round(confidence, 4),
                    source="rules",
                    signals=[
                        {
                            "source": source,
                            "signal": candidate["name"],
                            "video_count": candidate["video_count"],
                        }
                        for source in candidate["sources"]
                    ],
                    classifier_version="series-rules-v1",
                )
        return candidates
