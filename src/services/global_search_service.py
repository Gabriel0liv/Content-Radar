from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.models.content_item import ContentItem
from src.models.reference import ReferenceSource, Transcript, TranscriptSegment
from src.models.topic import ContentItemTopic, Topic
from src.models.video_workshop import VideoProject
from src.schemas.global_search import (
    GlobalContentResult,
    GlobalIdeaResult,
    GlobalReferenceResult,
    GlobalSearchResponse,
    GlobalTranscriptResult,
)


def _normalize(value: Optional[str]) -> str:
    return " ".join((value or "").casefold().split())


def text_rank(query: str, title: Optional[str], body: Optional[str]) -> float:
    needle = _normalize(query)
    title_norm = _normalize(title)
    body_norm = _normalize(body)
    if not needle:
        return 0.0
    if title_norm == needle:
        return 4.0
    if title_norm.startswith(needle):
        return 3.0
    if needle in title_norm:
        return 2.0
    if needle in body_norm:
        return 1.0
    return 0.0


def build_excerpt(text: str, query: str, max_chars: int = 180) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= max_chars:
        return compact
    needle = _normalize(query)
    haystack = compact.casefold()
    index = haystack.find(needle)
    if index < 0:
        return compact[: max_chars - 1].rstrip() + "…"
    half = max_chars // 2
    start = max(0, index - half)
    end = min(len(compact), start + max_chars)
    if end - start < max_chars:
        start = max(0, end - max_chars)
    excerpt = compact[start:end].strip()
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(compact):
        excerpt = excerpt + "…"
    return excerpt


class GlobalSearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, query: str, limit: int = 8) -> GlobalSearchResponse:
        term = query.strip()
        pattern = f"%{term}%"
        candidate_limit = max(limit * 4, 20)

        topic_item_ids = (
            self.db.query(ContentItemTopic.content_item_id)
            .join(Topic, Topic.id == ContentItemTopic.topic_id)
            .filter(Topic.name.ilike(pattern), ContentItemTopic.confidence >= 0.5)
            .subquery()
        )

        content_rows = (
            self.db.query(ContentItem)
            .filter(
                or_(
                    ContentItem.title.ilike(pattern),
                    ContentItem.description.ilike(pattern),
                    ContentItem.id.in_(topic_item_ids),
                )
            )
            .limit(candidate_limit)
            .all()
        )
        content_results = []
        for item in content_rows:
            rank = text_rank(term, item.title, item.description)
            if rank == 0.0:
                rank = 1.5
            content_results.append(
                GlobalContentResult(
                    id=item.id,
                    title=item.title,
                    url=item.url,
                    source=item.source,
                    channel_title=item.channel_title,
                    performance_ratio=item.performance_ratio,
                    match_rank=rank,
                )
            )
        content_results.sort(key=lambda row: (-row.match_rank, -(row.performance_ratio or 0.0), row.id))

        reference_rows = (
            self.db.query(ReferenceSource)
            .filter(
                or_(
                    ReferenceSource.title.ilike(pattern),
                    ReferenceSource.description.ilike(pattern),
                    ReferenceSource.channel_title.ilike(pattern),
                )
            )
            .limit(candidate_limit)
            .all()
        )
        reference_results = [
            GlobalReferenceResult(
                id=source.id,
                title=source.title,
                source_url=source.source_url,
                channel_title=source.channel_title,
                match_rank=text_rank(term, source.title, f"{source.description or ''} {source.channel_title or ''}"),
            )
            for source in reference_rows
        ]
        reference_results.sort(key=lambda row: (-row.match_rank, row.id))

        transcript_rows = (
            self.db.query(TranscriptSegment, Transcript, ReferenceSource)
            .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
            .join(ReferenceSource, ReferenceSource.id == Transcript.reference_source_id)
            .filter(Transcript.is_active.is_(True), TranscriptSegment.text.ilike(pattern))
            .limit(candidate_limit)
            .all()
        )
        transcript_results = [
            GlobalTranscriptResult(
                reference_source_id=source.id,
                transcript_id=transcript.id,
                segment_id=segment.id,
                video_title=source.title,
                start_time=segment.start_time,
                end_time=segment.end_time,
                matched_excerpt=build_excerpt(segment.text, term),
                match_rank=1.0,
            )
            for segment, transcript, source in transcript_rows
        ]
        transcript_results.sort(key=lambda row: (row.reference_source_id, row.start_time or 0.0, row.segment_id))

        idea_rows = (
            self.db.query(VideoProject)
            .filter(
                or_(
                    VideoProject.title.ilike(pattern),
                    VideoProject.description.ilike(pattern),
                    VideoProject.niche.ilike(pattern),
                )
            )
            .limit(candidate_limit)
            .all()
        )
        idea_results = [
            GlobalIdeaResult(
                id=idea.id,
                title=idea.title,
                description=idea.description,
                niche=idea.niche,
                status=idea.status,
                match_rank=text_rank(term, idea.title, f"{idea.description or ''} {idea.niche or ''}"),
            )
            for idea in idea_rows
        ]
        idea_results.sort(key=lambda row: (-row.match_rank, row.id))

        return GlobalSearchResponse(
            query=term,
            content_items=content_results[:limit],
            references=reference_results[:limit],
            transcript_matches=transcript_results[:limit],
            ideas=idea_results[:limit],
        )
