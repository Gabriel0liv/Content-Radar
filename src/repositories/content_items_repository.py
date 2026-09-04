from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from src.models.content_item import ContentItem, ContentItemEvent
from src.schemas.content_item import ContentItemCreate

class ContentItemsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, item_id: int) -> Optional[ContentItem]:
        return self.db.query(ContentItem).filter(ContentItem.id == item_id).first()

    def get_by_source_external_id(self, source: str, external_id: str) -> Optional[ContentItem]:
        return self.db.query(ContentItem).filter(
            ContentItem.source == source,
            ContentItem.external_id == external_id
        ).first()

    def get_by_youtube_video_id(self, youtube_video_id: str) -> Optional[ContentItem]:
        if not youtube_video_id:
            return None
        return self.db.query(ContentItem).filter(
            ContentItem.youtube_video_id == youtube_video_id
        ).order_by(ContentItem.id.asc()).first()

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
        min_performance_ratio: Optional[float] = None,
        sort_by: Optional[str] = "score",
        sort_order: Optional[str] = "desc",
    ) -> Tuple[List[ContentItem], int]:
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
        if min_performance_ratio is not None:
            query = query.filter(ContentItem.performance_ratio >= min_performance_ratio)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (ContentItem.title.ilike(search_pattern)) |
                (func.coalesce(ContentItem.description, '').ilike(search_pattern))
            )

        total = query.count()
        sorting_whitelist = {
            "score": ContentItem.score,
            "views": ContentItem.views,
            "published_at": ContentItem.published_at,
            "collected_at": ContentItem.collected_at,
            "views_per_day": ContentItem.views_per_day,
            "performance_ratio": ContentItem.performance_ratio,
            "last_seen_at": ContentItem.last_seen_at,
        }
        sort_column = sorting_whitelist.get(sort_by, ContentItem.score)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc().nullslast(), ContentItem.published_at.asc())
        else:
            query = query.order_by(sort_column.desc().nullslast(), ContentItem.published_at.desc())
        return query.offset(offset).limit(limit).all(), total

    def save(self, item: ContentItem) -> ContentItem:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def upsert(self, item_in: ContentItemCreate) -> ContentItem:
        db_item = self.get_by_source_external_id(item_in.source, item_in.external_id)
        if db_item:
            for field in (
                "title", "description", "url", "channel_title", "channel_id",
                "youtube_video_id", "youtube_category_id", "youtube_category_name",
                "youtube_tags_json", "youtube_topics_json", "topic_classification_version",
                "performance_ratio", "performance_baseline_samples",
                "published_at", "views", "likes", "comments", "views_per_day", "score",
                "topic_seed", "discovery_query", "language", "country_code", "raw_json",
            ):
                setattr(db_item, field, getattr(item_in, field))
            db_item.last_seen_at = datetime.now(timezone.utc)
            if item_in.search_config_id is not None:
                db_item.search_config_id = item_in.search_config_id
            if item_in.search_run_id is not None:
                db_item.search_run_id = item_in.search_run_id
            self.db.commit()
            self.db.refresh(db_item)
            return db_item

        item_data = item_in.model_dump()
        item_data["status"] = "new"
        db_item = ContentItem(**item_data)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return db_item

    def get_summary(self) -> dict:
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
            "max_views": max_views,
        }
