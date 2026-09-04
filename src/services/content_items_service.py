from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from src.repositories.content_items_repository import ContentItemsRepository
from src.schemas.content_item import ContentItemCreate, ContentItemCurationUpdate
from src.services.channel_profile_service import ChannelProfileService

class ContentItemsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ContentItemsRepository(db)
        self.channel_profiles = ChannelProfileService(db)

    def get_item(self, item_id: int):
        return self.repo.get_by_id(item_id)

    def list_items(
        self,
        limit: int = 500,
        offset: int = 0,
        search: Optional[str] = None,
        source: Optional[str] = None,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        topic_seed: Optional[str] = None,
        min_score: Optional[float] = None,
        min_views: Optional[int] = None,
        min_performance_ratio: Optional[float] = None,
        sort_by: Optional[str] = "score",
        sort_order: Optional[str] = "desc",
    ):
        items, total = self.repo.list(
            limit=limit,
            offset=offset,
            search=search,
            source=source,
            content_type=content_type,
            status=status,
            topic_seed=topic_seed,
            min_score=min_score,
            min_views=min_views,
            min_performance_ratio=min_performance_ratio,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def _apply_status_transitions(self, item, status: str):
        item.status = status
        item.last_seen_at = datetime.now(timezone.utc)
        if status == "reviewed" and not item.reviewed_at:
            item.reviewed_at = datetime.now(timezone.utc)
        elif status == "selected" and not item.selected_at:
            item.selected_at = datetime.now(timezone.utc)

    def update_item_status(self, item_id: int, status: str):
        item = self.repo.get_by_id(item_id)
        if not item:
            return None
        self._apply_status_transitions(item, status)
        return self.repo.save(item)

    def update_item_curation(self, item_id: int, curation_update: ContentItemCurationUpdate):
        item = self.repo.get_by_id(item_id)
        if not item:
            return None
        update_data = curation_update.model_dump(exclude_unset=True)
        if "notes" in update_data:
            item.notes = update_data["notes"]
        if "production_notes" in update_data:
            item.production_notes = update_data["production_notes"]
        if "rejected_reason" in update_data:
            item.rejected_reason = update_data["rejected_reason"]
        if "status" in update_data and update_data["status"] is not None:
            self._apply_status_transitions(item, update_data["status"])
        else:
            item.last_seen_at = datetime.now(timezone.utc)
        return self.repo.save(item)

    def ingest_items(self, items: List[ContentItemCreate]):
        ingested = []
        touched_channels = set()
        for payload in items:
            item = self.repo.upsert(payload)
            if item.channel_id:
                metrics = self.channel_profiles.metrics_for_item(item)
                item.performance_ratio = metrics["performance_ratio"]
                item.performance_baseline_samples = metrics["performance_baseline_samples"]
                item = self.repo.save(item)
                touched_channels.add(item.channel_id)
            ingested.append(item)
        for channel_id in touched_channels:
            self.channel_profiles.recompute(channel_id)
        return ingested

    def get_summary_stats(self):
        return self.repo.get_summary()
