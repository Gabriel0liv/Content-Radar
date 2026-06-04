from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.db.session import get_db
from src.schemas.content_item import ContentItemCreate, ContentItem
from src.services.content_items_service import ContentItemsService

router = APIRouter()

@router.post("/n8n", response_model=List[ContentItem])
def ingest_n8n(items: List[ContentItemCreate], db: Session = Depends(get_db)):
    """
    Ingest a list of content items from n8n.
    Performs upsert operations, preventing overwrites of curated fields.
    """
    service = ContentItemsService(db)
    return service.ingest_items(items)
