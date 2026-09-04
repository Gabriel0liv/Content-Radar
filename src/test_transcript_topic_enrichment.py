from types import SimpleNamespace

from src.services.transcript_topic_enrichment import should_replace_association


def test_manual_topic_association_is_never_overwritten_by_classifier():
    existing = SimpleNamespace(source="manual", confidence=0.55)
    assert should_replace_association(existing, inferred_confidence=0.99) is False


def test_inferred_association_can_be_refreshed_by_new_classifier_result():
    existing = SimpleNamespace(source="rules", confidence=0.62)
    assert should_replace_association(existing, inferred_confidence=0.81) is True


def test_missing_association_accepts_inferred_result():
    assert should_replace_association(None, inferred_confidence=0.74) is True
