from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from src.models.topic import ContentItemTopic, Topic
from src.schemas.topics import TopicCreate, normalize_topic_name


class TopicsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_topic(self, topic_id: int) -> Optional[Topic]:
        return self.db.query(Topic).filter(Topic.id == topic_id).first()

    def find_topic(self, normalized_name: str, topic_type: str, parent_id: Optional[int] = None) -> Optional[Topic]:
        return self.db.query(Topic).filter(
            Topic.normalized_name == normalized_name,
            Topic.type == topic_type,
            Topic.parent_id == parent_id,
        ).first()

    def create_topic(self, payload: TopicCreate) -> Topic:
        normalized_name = normalize_topic_name(payload.name)
        existing = self.find_topic(normalized_name, payload.type, payload.parent_id)
        if existing:
            return existing
        topic = Topic(
            name=payload.name,
            normalized_name=normalized_name,
            type=payload.type,
            parent_id=payload.parent_id,
            status=payload.status,
        )
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic

    def list_topics(self, topic_type: Optional[str] = None, status: str = "active") -> List[Topic]:
        query = self.db.query(Topic)
        if topic_type:
            query = query.filter(Topic.type == topic_type)
        if status:
            query = query.filter(Topic.status == status)
        return query.order_by(Topic.name.asc()).all()

    def upsert_content_topic(
        self,
        content_item_id: int,
        topic_id: int,
        confidence: float,
        source: str,
        signals: List[Dict],
        classifier_version: Optional[str],
    ) -> ContentItemTopic:
        association = self.db.query(ContentItemTopic).filter(
            ContentItemTopic.content_item_id == content_item_id,
            ContentItemTopic.topic_id == topic_id,
        ).first()
        if association is None:
            association = ContentItemTopic(
                content_item_id=content_item_id,
                topic_id=topic_id,
                confidence=confidence,
                source=source,
                signals_json=signals,
                classifier_version=classifier_version,
            )
            self.db.add(association)
        else:
            association.confidence = confidence
            association.source = source
            association.signals_json = signals
            association.classifier_version = classifier_version
        self.db.commit()
        self.db.refresh(association)
        return association
