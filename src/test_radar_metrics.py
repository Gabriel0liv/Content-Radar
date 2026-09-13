from types import SimpleNamespace

from src.models.content_item import ContentItem
from src.schemas.content_item import ContentItemCreate
from src.services.channel_profile_service import calculate_performance_ratio


def test_content_item_model_exposes_performance_fields():
    assert hasattr(ContentItem, "performance_ratio")
    assert hasattr(ContentItem, "performance_baseline_samples")


def test_content_item_schema_accepts_performance_fields():
    item = ContentItemCreate(
        source="youtube",
        external_id="dQw4w9WgXcQ",
        title="Example",
        url="https://youtu.be/dQw4w9WgXcQ",
        performance_ratio=3.25,
        performance_baseline_samples=7,
    )
    assert item.performance_ratio == 3.25
    assert item.performance_baseline_samples == 7


def test_low_sample_ratio_is_still_available_but_marked_low_confidence():
    profile = SimpleNamespace(recent_views_per_day_median=10_000, sample_count=3)
    result = calculate_performance_ratio(30_000, profile)
    assert result["performance_ratio"] == 3.0
    assert result["performance_baseline_confidence"] == "low"
