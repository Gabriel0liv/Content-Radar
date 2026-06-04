from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.db.session import get_db
from src.schemas.content_item import ContentItem, ContentItemStatusUpdate
from src.services.content_items_service import ContentItemsService

router = APIRouter()

@router.get("", response_model=List[ContentItem])
def get_content_items(
    limit: int = Query(500, ge=1, le=2000),
    source: Optional[str] = None,
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    topic_seed: Optional[str] = None,
    min_score: Optional[float] = None,
    min_views: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List content items with optional query parameters.
    """
    service = ContentItemsService(db)
    return service.list_items(
        limit=limit,
        source=source,
        content_type=content_type,
        status=status,
        topic_seed=topic_seed,
        min_score=min_score,
        min_views=min_views
    )

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
