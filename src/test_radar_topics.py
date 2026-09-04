from src.models.topic import ContentItemTopic, Topic
from src.schemas.content_item import DetectedTopic


def test_detected_topic_schema_exposes_explainable_fields():
    topic = DetectedTopic(id=7, name="Minecraft", type="topic", confidence=0.91, source="rules")
    assert topic.name == "Minecraft"
    assert topic.confidence == 0.91
    assert topic.source == "rules"


def test_content_item_detected_topics_property_orders_by_confidence():
    from src.models.content_item import ContentItem

    item = ContentItem()
    lore = Topic(id=2, name="Lore", normalized_name="lore", type="format", status="active")
    minecraft = Topic(id=1, name="Minecraft", normalized_name="minecraft", type="topic", status="active")

    item.topic_associations = [
        ContentItemTopic(confidence=0.62, source="rules", topic=lore),
        ContentItemTopic(confidence=0.94, source="transcript", topic=minecraft),
    ]

    assert [topic["name"] for topic in item.detected_topics] == ["Minecraft", "Lore"]
