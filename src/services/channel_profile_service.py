from datetime import datetime, timezone
from statistics import median
from types import SimpleNamespace
from typing import Iterable

from sqlalchemy.orm import Session

from src.models.channel_profile import ChannelProfile
from src.repositories.channel_profiles_repository import ChannelProfilesRepository


def baseline_confidence(sample_count: int) -> str:
    if sample_count >= 5:
        return "normal"
    if sample_count >= 2:
        return "low"
    return "insufficient"


def calculate_channel_baseline(samples: Iterable) -> dict:
    valid = [sample for sample in samples if sample is not None]
    views = [float(sample.views) for sample in valid if getattr(sample, "views", None) is not None]
    views_per_day = [
        float(sample.views_per_day)
        for sample in valid
        if getattr(sample, "views_per_day", None) is not None and float(sample.views_per_day) > 0
    ]
    sample_count = len(views_per_day)
    return {
        "sample_count": sample_count,
        "recent_views_median": median(views) if views else None,
        "recent_views_per_day_median": median(views_per_day) if views_per_day else None,
        "recent_age_adjusted_samples": sample_count,
    }


def calculate_performance_ratio(video_views_per_day, profile) -> dict:
    sample_count = int(getattr(profile, "sample_count", 0) or 0) if profile else 0
    confidence = baseline_confidence(sample_count)
    baseline = float(getattr(profile, "recent_views_per_day_median", 0) or 0) if profile else 0.0
    ratio = None
    if confidence != "insufficient" and baseline > 0 and video_views_per_day is not None:
        ratio = round(float(video_views_per_day) / baseline, 4)
    return {
        "performance_ratio": ratio,
        "performance_baseline_samples": sample_count,
        "performance_baseline_confidence": confidence,
    }


class ChannelProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ChannelProfilesRepository(db)

    def recompute(self, channel_id: str) -> ChannelProfile:
        samples = self.repo.list_recent_content(channel_id, limit=30)
        baseline = calculate_channel_baseline(samples)
        profile = self.repo.get_by_channel_id(channel_id) or ChannelProfile(channel_id=channel_id)
        profile.channel_title = next((item.channel_title for item in samples if item.channel_title), profile.channel_title)
        profile.sample_count = baseline["sample_count"]
        profile.recent_views_median = baseline["recent_views_median"]
        profile.recent_views_per_day_median = baseline["recent_views_per_day_median"]
        profile.recent_age_adjusted_samples = baseline["recent_age_adjusted_samples"]
        profile.dominant_topics_json = self.repo.dominant_topics(channel_id)
        profile.last_profiled_at = datetime.now(timezone.utc)
        return self.repo.save(profile)

    def metrics_for_item(self, item) -> dict:
        if not getattr(item, "channel_id", None):
            return {
                "performance_ratio": None,
                "performance_baseline_samples": 0,
                "performance_baseline_confidence": "insufficient",
            }
        samples = self.repo.list_recent_content(
            item.channel_id,
            limit=30,
            exclude_content_item_id=item.id,
        )
        baseline = calculate_channel_baseline(samples)
        temporary_profile = SimpleNamespace(
            recent_views_per_day_median=baseline["recent_views_per_day_median"],
            sample_count=baseline["sample_count"],
        )
        return calculate_performance_ratio(item.views_per_day, temporary_profile)
