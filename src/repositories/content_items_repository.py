from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from src.models.content_item import ContentItem, ContentItemEvent
from src.schemas.content_item import ContentItemCreate, ContentItemCurationUpdate

class ContentItemsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: int) -> Optional[ContentItem]:
        """
        Retrieves a ContentItem by primary key.
        """
        return self.db.query(ContentItem).filter(ContentItem.id == item_id).first()

    def get_by_source_external_id(self, source: str, external_id: str) -> Optional[ContentItem]:
        """
        Retrieves a ContentItem by unique combination of source and external_id.
        """
        return self.db.query(ContentItem).filter(
            ContentItem.source == source,
            ContentItem.external_id == external_id
        ).first()

    def list(
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
    ) -> Tuple[List[ContentItem], int]:
        """
        Queries content_items with optional filters, pagination, search, and sorting.
        """
        query = self.db.query(ContentItem)
        if source and source != "Todos":
            query = query.filter(ContentItem.source == source)
        if content_type and content_type != "Todos":
            query = query.filter(ContentItem.content_type == content_type)
        if status and status != "Todos":
            query = query.filter(ContentItem.status == status)
        if topic_seed and topic_seed != "Todos":
            query = query.filter(ContentItem.topic_seed == topic_seed)
        if min_score is not None:
            query = query.filter(ContentItem.score >= min_score)
        if min_views is not None:
            query = query.filter(ContentItem.views >= min_views)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (ContentItem.title.ilike(search_pattern)) |
                (ContentItem.description.ilike(search_pattern))
            )
        
        total = query.count()
        
        # Whitelist of allowed columns for sorting
        sorting_whitelist = {
            "score": ContentItem.score,
            "views": ContentItem.views,
            "published_at": ContentItem.published_at,
            "collected_at": ContentItem.collected_at,
            "views_per_day": ContentItem.views_per_day
        }
        
        sort_column = sorting_whitelist.get(sort_by, ContentItem.score)
        
        if sort_order == "asc":
            query = query.order_by(sort_column.asc(), ContentItem.published_at.asc())
        else:
            query = query.order_by(sort_column.desc(), ContentItem.published_at.desc())
            
        items = query.offset(offset).limit(limit).all()
        return items, total

    def save(self, item: ContentItem) -> ContentItem:
        """
        Saves and commits a ContentItem instance.
        """
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def upsert(self, item_in: ContentItemCreate) -> ContentItem:
        """
        Inserts or updates a content item.
        If the item already exists: updates stats, score, and raw_json while preserving user curation status/notes.
        """
        db_item = self.get_by_source_external_id(item_in.source, item_in.external_id)
        if db_item:
            # Update fields but preserve manual curation data and status
            db_item.title = item_in.title
            db_item.description = item_in.description
            db_item.url = item_in.url
            db_item.channel_title = item_in.channel_title
            db_item.published_at = item_in.published_at
            db_item.views = item_in.views
            db_item.likes = item_in.likes
            db_item.comments = item_in.comments
            db_item.views_per_day = item_in.views_per_day
            db_item.score = item_in.score
            db_item.topic_seed = item_in.topic_seed
            db_item.discovery_query = item_in.discovery_query
            db_item.language = item_in.language
            db_item.country_code = item_in.country_code
            db_item.raw_json = item_in.raw_json
            db_item.last_seen_at = datetime.now(timezone.utc)
            
            self.db.commit()
            self.db.refresh(db_item)
            return db_item
        else:
            # Create a fresh record
            item_data = item_in.model_dump()
            item_data["status"] = "new"
            db_item = ContentItem(**item_data)
            self.db.add(db_item)
            self.db.commit()
            self.db.refresh(db_item)
            return db_item

    def get_summary(self) -> dict:
        """
        Aggregates metrics: total count, new count, counts by source, max views, max score.
        """
        total_items = self.db.query(ContentItem).count()
        new_items = self.db.query(ContentItem).filter(ContentItem.status == 'new').count()
        
        max_res = self.db.query(
            func.coalesce(func.max(ContentItem.score), 0.0),
            func.coalesce(func.max(ContentItem.views), 0)
        ).first()
        max_score = float(max_res[0]) if max_res else 0.0
        max_views = int(max_res[1]) if max_res else 0
        
        source_res = self.db.query(ContentItem.source, func.count(ContentItem.id)).group_by(ContentItem.source).all()
        items_by_source = {row[0]: row[1] for row in source_res}
        
        return {
            "total_items": total_items,
            "new_items": new_items,
            "items_by_source": items_by_source,
            "max_score": max_score,
            "max_views": max_views
        }
