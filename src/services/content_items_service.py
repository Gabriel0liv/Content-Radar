from sqlalchemy.orm import Session
from typing import List, Optional
from src.repositories.content_items_repository import ContentItemsRepository
from src.schemas.content_item import ContentItemCreate

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
        source: Optional[str] = None,
        content_type: Optional[str] = None,
        status: Optional[str] = None,
        topic_seed: Optional[str] = None,
        min_score: Optional[float] = None,
        min_views: Optional[int] = None
    ):
        """
        Lists items filtering on limits, source, types, status, topic, min score and min views.
        """
        return self.repo.list(
            limit=limit,
            source=source,
            content_type=content_type,
            status=status,
            topic_seed=topic_seed,
            min_score=min_score,
            min_views=min_views
        )

    def update_item_status(self, item_id: int, status: str):
        """
        Updates the status of a single content item.
        """
        return self.repo.update_status(item_id, status)

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
