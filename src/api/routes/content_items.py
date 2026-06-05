from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from src.db.session import get_db
from src.schemas.content_item import (
    ContentItem,
    ContentItemStatusUpdate,
    ContentItemCurationUpdate,
    ContentItemListResponse,
    ContentItemSummary
)
from src.services.content_items_service import ContentItemsService

router = APIRouter()

@router.get("", response_model=ContentItemListResponse)
def get_content_items(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, description="Search term matching title or description"),
    source: Optional[str] = None,
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    topic_seed: Optional[str] = None,
    min_score: Optional[float] = None,
    min_views: Optional[int] = None,
    sort_by: Literal["score", "views", "published_at", "collected_at", "views_per_day"] = "score",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db)
):
    """
    List content items with optional query parameters, search, pagination, and sorting.
    """
    service = ContentItemsService(db)
    return service.list_items(
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

@router.get("/summary", response_model=ContentItemSummary)
def get_content_items_summary(db: Session = Depends(get_db)):
    """
    Fetch aggregated metrics (total, new, by source, max score, max views).
    """
    service = ContentItemsService(db)
    return service.get_summary_stats()

@router.get("/{item_id}", response_model=ContentItem)
def get_content_item(item_id: int, db: Session = Depends(get_db)):
    """
    Fetch details of a single content item.
    """
    service = ContentItemsService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")
    return item

@router.patch("/{item_id}", response_model=ContentItem)
def update_item_curation(
    item_id: int,
    curation_update: ContentItemCurationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update curation fields of a content item (status, notes, production_notes, rejected_reason).
    """
    service = ContentItemsService(db)
    item = service.update_item_curation(item_id, curation_update)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")
    return item

@router.patch("/{item_id}/status", response_model=ContentItem)
def update_item_status(
    item_id: int,
    status_update: ContentItemStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the status of a content item and record associated transition timestamps.
    """
    service = ContentItemsService(db)
    item = service.update_item_status(item_id, status_update.status)
    if not item:
        raise HTTPException(status_code=404, detail="Content item not found")
    return item
