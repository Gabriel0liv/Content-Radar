from types import SimpleNamespace

from src.services.channel_profile_service import (
    baseline_confidence,
    calculate_channel_baseline,
    calculate_performance_ratio,
)


def sample(views, views_per_day):
    return SimpleNamespace(views=views, views_per_day=views_per_day)


def test_channel_baseline_uses_median_not_mean():
    samples = [
        sample(100_000, 10_000),
        sample(120_000, 12_000),
        sample(140_000, 14_000),
        sample(160_000, 16_000),
        sample(10_000_000, 1_000_000),
    ]

    baseline = calculate_channel_baseline(samples)

    assert baseline["sample_count"] == 5
    assert baseline["recent_views_median"] == 140_000
    assert baseline["recent_views_per_day_median"] == 14_000


def test_baseline_confidence_thresholds_are_explicit():
    assert baseline_confidence(1) == "insufficient"
    assert baseline_confidence(2) == "low"
    assert baseline_confidence(4) == "low"
    assert baseline_confidence(5) == "normal"


def test_performance_ratio_uses_views_per_day_baseline():
    profile = SimpleNamespace(recent_views_per_day_median=20_000, sample_count=8)
    result = calculate_performance_ratio(90_000, profile)

    assert result["performance_ratio"] == 4.5
    assert result["performance_baseline_samples"] == 8
    assert result["performance_baseline_confidence"] == "normal"


def test_performance_ratio_is_none_without_enough_history():
    profile = SimpleNamespace(recent_views_per_day_median=20_000, sample_count=1)
    result = calculate_performance_ratio(90_000, profile)

    assert result["performance_ratio"] is None
    assert result["performance_baseline_confidence"] == "insufficient"
