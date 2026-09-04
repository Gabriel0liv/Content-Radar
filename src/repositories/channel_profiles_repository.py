from typing import List, Optional

from sqlalchemy.orm import Session

from src.models.channel_profile import ChannelProfile
from src.models.content_item import ContentItem
from src.models.topic import ContentItemTopic, Topic


class ChannelProfilesRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_channel_id(self, channel_id: str) -> Optional[ChannelProfile]:
        return self.db.query(ChannelProfile).filter(ChannelProfile.channel_id == channel_id).first()

    def list_recent_content(self, channel_id: str, limit: int = 30) -> List[ContentItem]:
        return (
            self.db.query(ContentItem)
            .filter(ContentItem.channel_id == channel_id)
            .order_by(ContentItem.published_at.desc().nullslast(), ContentItem.id.desc())
            .limit(limit)
            .all()
        )

    def dominant_topics(self, channel_id: str, limit: int = 8) -> List[dict]:
        rows = (
            self.db.query(Topic.name, Topic.type, ContentItemTopic.confidence)
            .join(ContentItemTopic, ContentItemTopic.topic_id == Topic.id)
            .join(ContentItem, ContentItem.id == ContentItemTopic.content_item_id)
            .filter(ContentItem.channel_id == channel_id)
            .all()
        )
        aggregated = {}
        for name, topic_type, confidence in rows:
            key = (name, topic_type)
            entry = aggregated.setdefault(key, {"name": name, "type": topic_type, "score": 0.0, "count": 0})
            entry["score"] += float(confidence or 0.0)
            entry["count"] += 1
        ranked = sorted(
            aggregated.values(),
            key=lambda item: (-item["count"], -item["score"], item["name"]),
        )[:limit]
        for item in ranked:
            item["score"] = round(item["score"], 4)
        return ranked

    def save(self, profile: ChannelProfile) -> ChannelProfile:
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
