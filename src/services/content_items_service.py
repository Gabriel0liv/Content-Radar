from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from src.repositories.content_items_repository import ContentItemsRepository
from src.schemas.content_item import ContentItemCreate, ContentItemCurationUpdate

class ContentItemsService:
    def __init__(self, db: Session):
        self.repo = ContentItemsRepository(db)

    def get_item(self, item_id: int):
        """
        Fetches an item by ID.
        """
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
        sort_by: Optional[str] = "score",
        sort_order: Optional[str] = "desc"
    ):
        """
        Lists items filtering on limits, offset, search, source, types, status, topic, min score, min views, and sorting.
        """
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
            sort_by=sort_by,
            sort_order=sort_order
        )
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    def _apply_status_transitions(self, item, status: str):
        """
        Centralized logic for status transitions and associated timestamps.
        """
        item.status = status
        item.last_seen_at = datetime.now(timezone.utc)
        if status == "reviewed" and not item.reviewed_at:
            item.reviewed_at = datetime.now(timezone.utc)
        elif status == "selected" and not item.selected_at:
            item.selected_at = datetime.now(timezone.utc)

    def update_item_status(self, item_id: int, status: str):
        """
        Updates the status of a single content item, using centralized transition logic.
        """
        item = self.repo.get_by_id(item_id)
        if not item:
            return None
        self._apply_status_transitions(item, status)
        return self.repo.save(item)

    def update_item_curation(self, item_id: int, curation_update: ContentItemCurationUpdate):
        """
        Updates only permitted curation fields of a single content item.
        """
        item = self.repo.get_by_id(item_id)
        if not item:
            return None
            
        update_data = curation_update.model_dump(exclude_unset=True)
        
        # update notes, production_notes, and rejected_reason
        if "notes" in update_data:
            item.notes = update_data["notes"]
        if "production_notes" in update_data:
            item.production_notes = update_data["production_notes"]
        if "rejected_reason" in update_data:
            item.rejected_reason = update_data["rejected_reason"]
            
        # status and transition logic
        if "status" in update_data and update_data["status"] is not None:
            self._apply_status_transitions(item, update_data["status"])
        else:
            item.last_seen_at = datetime.now(timezone.utc)
            
        return self.repo.save(item)

    def ingest_items(self, items: List[ContentItemCreate]):
        """
        Loops through list of items and calls repository upsert for each one.
        """
        ingested = []
        for item in items:
            ingested.append(self.repo.upsert(item))
        return ingested

    def get_summary_stats(self):
        """
        Compiles summary statistics from database.
        """
        return self.repo.get_summary()
