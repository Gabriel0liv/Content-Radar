from typing import List, Optional

from pydantic import BaseModel


class GlobalContentResult(BaseModel):
    id: int
    title: str
    url: str
    source: str
    channel_title: Optional[str] = None
    performance_ratio: Optional[float] = None
    match_rank: float


class GlobalReferenceResult(BaseModel):
    id: int
    title: str
    source_url: str
    channel_title: Optional[str] = None
    match_rank: float


class GlobalTranscriptResult(BaseModel):
    reference_source_id: int
    transcript_id: int
    segment_id: int
    video_title: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    matched_excerpt: str
    match_rank: float


class GlobalIdeaResult(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    niche: Optional[str] = None
    status: str
    match_rank: float


class GlobalSearchResponse(BaseModel):
    query: str
    content_items: List[GlobalContentResult]
    references: List[GlobalReferenceResult]
    transcript_matches: List[GlobalTranscriptResult]
    ideas: List[GlobalIdeaResult]
