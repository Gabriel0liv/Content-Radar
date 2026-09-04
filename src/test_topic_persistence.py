from types import SimpleNamespace

from src.services.topic_classification_service import should_preserve_existing_topic


def test_manual_topic_assignment_is_preserved():
    existing = SimpleNamespace(source="manual")
    assert should_preserve_existing_topic(existing) is True


def test_rules_topic_can_be_refreshed():
    existing = SimpleNamespace(source="rules")
    assert should_preserve_existing_topic(existing) is False


def test_missing_topic_can_be_created():
    assert should_preserve_existing_topic(None) is False
