from typing import Optional

from sqlalchemy.orm import Session

from src.repositories.content_items_repository import ContentItemsRepository
from src.repositories.topics_repository import TopicsRepository
from src.services.topic_classifier import TopicClassifier


def should_replace_association(existing, inferred_confidence: float) -> bool:
    if existing is None:
        return True
    if getattr(existing, "source", None) == "manual":
        return False
    return True


def enrich_topics_from_transcript(
    db: Session,
    youtube_video_id: str,
    transcript_text: str,
    channel_profile=None,
) -> int:
    if not youtube_video_id or not transcript_text.strip():
        return 0

    content_repo = ContentItemsRepository(db)
    topics_repo = TopicsRepository(db)
    item = content_repo.get_by_youtube_video_id(youtube_video_id)
    if item is None:
        return 0

    classifications = TopicClassifier().classify_content_item(
        item,
        channel_profile=channel_profile,
        transcript_text=transcript_text,
    )

    persisted = 0
    for result in classifications:
        topic = topics_repo.find_topic_by_name_any_type(result.topic)
        if topic is None:
            continue

        existing = topics_repo.get_content_topic(item.id, topic.id)
        if not should_replace_association(existing, result.confidence):
            continue

        topics_repo.upsert_content_topic(
            content_item_id=item.id,
            topic_id=topic.id,
            confidence=result.confidence,
            source="transcript",
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

    item.topic_classification_version = TopicClassifier().rules.get("_version", None) or "rules-v1"
    content_repo.save(item)
    return persisted
