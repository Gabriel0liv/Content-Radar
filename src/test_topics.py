from src.models.topic import Topic
from src.schemas.topics import TopicCreate


def test_topic_schema_supports_expected_types():
    topic = TopicCreate(name="Minecraft", type="topic")
    subtopic = TopicCreate(name="Minecraft Horror", type="subtopic", parent_id=1)
    fmt = TopicCreate(name="SMP", type="format")
    series = TopicCreate(name="Drathos SMP", type="series")

    assert topic.type == "topic"
    assert subtopic.type == "subtopic"
    assert fmt.type == "format"
    assert series.type == "series"


def test_topic_model_exposes_normalized_identity_fields():
    assert hasattr(Topic, "normalized_name")
    assert hasattr(Topic, "type")
    assert hasattr(Topic, "parent_id")
