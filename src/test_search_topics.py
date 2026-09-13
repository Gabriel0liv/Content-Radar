from types import SimpleNamespace

from src.schemas.search import SearchConfigCreate
from src.services.search_service import content_matches_structured_search


def test_search_config_accepts_structured_topic_criteria():
    config = SearchConfigCreate(
        name="Minecraft breakout",
        keywords_json=["minecraft"],
        included_topic_ids=[10, 11],
        excluded_topic_ids=[99],
        minimum_topic_confidence=0.7,
        minimum_performance_ratio=2.0,
    )
    assert config.included_topic_ids == [10, 11]
    assert config.minimum_topic_confidence == 0.7
    assert config.minimum_performance_ratio == 2.0


def test_structured_match_requires_topic_confidence_and_ratio():
    config = SimpleNamespace(
        included_topic_ids=[10],
        excluded_topic_ids=[],
        minimum_topic_confidence=0.7,
        minimum_performance_ratio=2.0,
    )
    item = SimpleNamespace(performance_ratio=3.5)
    topic_rows = [SimpleNamespace(topic_id=10, confidence=0.84)]
    assert content_matches_structured_search(item, topic_rows, config) is True


def test_excluded_topic_blocks_match_even_when_included_topic_matches():
    config = SimpleNamespace(
        included_topic_ids=[10],
        excluded_topic_ids=[99],
        minimum_topic_confidence=0.7,
        minimum_performance_ratio=None,
    )
    item = SimpleNamespace(performance_ratio=5.0)
    topic_rows = [
        SimpleNamespace(topic_id=10, confidence=0.91),
        SimpleNamespace(topic_id=99, confidence=0.88),
    ]
    assert content_matches_structured_search(item, topic_rows, config) is False
