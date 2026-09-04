from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.content_item import ContentItem
from src.models.discovery_term import DiscoveryTerm
from src.models.topic import Topic
from src.services.youtube_metadata_service import normalize_tag


STOP_TAGS = {
    "viral",
    "youtube",
    "video",
    "funny",
    "gaming",
    "game",
    "trending",
    "shorts",
    "short",
}


def discovery_term_score(video_count: int, channel_count: int, usage_count: int) -> float:
    breadth = float(channel_count) * 3.0
    coverage = float(video_count) * 1.4
    frequency = min(float(usage_count), float(video_count) * 2.0) * 0.25
    return round(breadth + coverage + frequency, 4)


def should_promote_tag(term: str, video_count: int, channel_count: int, manual_usage: int = 0) -> bool:
    normalized = normalize_tag(term)
    if not normalized or normalized in STOP_TAGS:
        return False
    if manual_usage > 0:
        return True
    return video_count >= 3 and channel_count >= 2


class DiscoveryTermsService:
    def __init__(self, db: Session):
        self.db = db

    def _upsert(
        self,
        normalized_term: str,
        display_name: str,
        term_type: str,
        entity_id: Optional[int],
        usage_count: int,
        video_count: int,
        channel_count: int,
        suppressed: bool = False,
    ) -> DiscoveryTerm:
        term = self.db.query(DiscoveryTerm).filter(
            DiscoveryTerm.normalized_term == normalized_term,
            DiscoveryTerm.type == term_type,
            DiscoveryTerm.entity_id == entity_id,
        ).first()
        if term is None:
            term = DiscoveryTerm(
                normalized_term=normalized_term,
                display_name=display_name,
                type=term_type,
                entity_id=entity_id,
            )
            self.db.add(term)
        term.usage_count = usage_count
        term.video_count = video_count
        term.channel_count = channel_count
        term.relevance_score = discovery_term_score(video_count, channel_count, usage_count)
        term.suppressed = suppressed
        term.last_seen_at = datetime.now(timezone.utc)
        return term

    def rebuild(self) -> int:
        self.db.query(DiscoveryTerm).delete(synchronize_session=False)

        count = 0
        topics = self.db.query(Topic).filter(Topic.status == "active").all()
        for topic in topics:
            self._upsert(
                normalized_term=topic.normalized_name,
                display_name=topic.name,
                term_type=topic.type,
                entity_id=topic.id,
                usage_count=1,
                video_count=0,
                channel_count=0,
                suppressed=False,
            )
            count += 1

        category_stats = defaultdict(lambda: {"videos": set(), "channels": set(), "display": None})
        tag_stats = defaultdict(lambda: {"videos": set(), "channels": set(), "display": None, "usage": 0})

        items = self.db.query(ContentItem).filter(ContentItem.source == "youtube").all()
        for item in items:
            if item.youtube_category_name:
                normalized = normalize_tag(item.youtube_category_name)
                stat = category_stats[normalized]
                stat["display"] = item.youtube_category_name
                stat["videos"].add(item.id)
                if item.channel_id:
                    stat["channels"].add(item.channel_id)

            seen_tags = set()
            for raw_tag in item.youtube_tags_json or []:
                normalized = normalize_tag(raw_tag)
                if not normalized:
                    continue
                stat = tag_stats[normalized]
                stat["display"] = stat["display"] or str(raw_tag)
                stat["usage"] += 1
                stat["videos"].add(item.id)
                if item.channel_id:
                    stat["channels"].add(item.channel_id)
                seen_tags.add(normalized)

        for normalized, stat in category_stats.items():
            self._upsert(
                normalized_term=normalized,
                display_name=stat["display"],
                term_type="youtube_category",
                entity_id=None,
                usage_count=len(stat["videos"]),
                video_count=len(stat["videos"]),
                channel_count=len(stat["channels"]),
            )
            count += 1

        for normalized, stat in tag_stats.items():
            video_count = len(stat["videos"])
            channel_count = len(stat["channels"])
            promoted = should_promote_tag(normalized, video_count, channel_count)
            self._upsert(
                normalized_term=normalized,
                display_name=stat["display"],
                term_type="tag",
                entity_id=None,
                usage_count=stat["usage"],
                video_count=video_count,
                channel_count=channel_count,
                suppressed=not promoted,
            )
            count += 1

        self.db.commit()
        return count

    def search(self, query: str, limit: int = 20) -> List[DiscoveryTerm]:
        normalized = normalize_tag(query)
        if not normalized:
            return []
        return (
            self.db.query(DiscoveryTerm)
            .filter(
                DiscoveryTerm.suppressed.is_(False),
                DiscoveryTerm.normalized_term.ilike(f"{normalized}%"),
            )
            .order_by(DiscoveryTerm.relevance_score.desc(), DiscoveryTerm.display_name.asc())
            .limit(limit)
            .all()
        )
