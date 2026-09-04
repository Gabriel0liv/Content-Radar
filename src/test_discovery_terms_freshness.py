from datetime import datetime, timedelta, timezone

from src.services.discovery_terms_service import index_is_stale


def test_empty_index_is_stale():
    now = datetime.now(timezone.utc)
    assert index_is_stale(None, now) is True


def test_newer_source_data_makes_index_stale():
    now = datetime.now(timezone.utc)
    assert index_is_stale(now - timedelta(minutes=5), now) is True


def test_newer_index_is_fresh():
    now = datetime.now(timezone.utc)
    assert index_is_stale(now, now - timedelta(minutes=5)) is False
