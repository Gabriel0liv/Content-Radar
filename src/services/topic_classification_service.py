from typing import Optional

from sqlalchemy.orm import Session

from src.repositories.channel_profiles_repository import ChannelProfilesRepository
from src.repositories.topics_repository import TopicsRepository
from src.services.topic_classifier import CLASSIFIER_VERSION, TopicClassifier


def should_preserve_existing_topic(existing) -> bool:
    return existing is not None and getattr(existing, "source", None) == "manual"


class TopicClassificationService:
    def __init__(self, db: Session):
        self.db = db
        self.topics_repo = TopicsRepository(db)
        self.channel_profiles_repo = ChannelProfilesRepository(db)
        self.classifier = TopicClassifier()

    def classify_and_persist(self, item, transcript_text: Optional[str] = None) -> int:
        channel_profile = None
        if getattr(item, "channel_id", None):
            channel_profile = self.channel_profiles_repo.get_by_channel_id(item.channel_id)

        results = self.classifier.classify_content_item(
            item,
            channel_profile=channel_profile,
            transcript_text=transcript_text,
        )

        persisted = 0
        for result in results:
            topic = self.topics_repo.find_topic_by_name_any_type(result.topic)
            if topic is None:
                continue
            existing = self.topics_repo.get_content_topic(item.id, topic.id)
            if should_preserve_existing_topic(existing):
                continue

            association_source = "transcript" if any(signal.source == "transcript" for signal in result.signals) else "rules"
            self.topics_repo.upsert_content_topic(
                content_item_id=item.id,
                topic_id=topic.id,
                confidence=result.confidence,
                source=association_source,
                signals=[
                    {
                        "source": signal.source,
                        "signal": signal.signal,
                        "weight": signal.weight,
                    }
                    for signal in result.signals
                ],
                classifier_version=result.classifier_version,
            )
            persisted += 1

        item.topic_classification_version = CLASSIFIER_VERSION
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return persisted
