from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DiscoveryTermRead(BaseModel):
    id: int
    normalized_term: str
    display_name: str
    type: str
    entity_id: Optional[int] = None
    usage_count: int
    video_count: int
    channel_count: int
    relevance_score: float
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True
