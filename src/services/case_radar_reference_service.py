from __future__ import annotations

from sqlalchemy.orm import Session

from src.models.case_radar import ResearchSource
from src.models.reference import ReferenceImportJob, ReferenceSource
from src.repositories.references_repository import ReferencesRepository
from src.schemas.references import ReferenceSourceCreate, extract_youtube_video_id


class CaseRadarReferenceError(ValueError):
    pass


class CaseRadarReferenceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.references = ReferencesRepository(db)

    def _get_source(self, source_id: int) -> ResearchSource:
        source = self.db.get(ResearchSource, source_id)
        if source is None:
            raise CaseRadarReferenceError("ResearchSource não encontrada")
        return source

    @staticmethod
    def _youtube_video_id(source: ResearchSource) -> str:
        candidate = (source.external_id or "").strip()
        if candidate:
            try:
                return extract_youtube_video_id(f"https://youtube.com/watch?v={candidate}")
            except ValueError:
                pass
        try:
            return extract_youtube_video_id(source.canonical_url)
        except ValueError as exc:
            raise CaseRadarReferenceError("Fonte YouTube sem video id válido") from exc

    def promote_to_reference(self, source_id: int) -> ReferenceSource:
        source = self._get_source(source_id)
        if source.reference_source_id is not None:
            existing = self.references.get_reference_source_by_id(source.reference_source_id)
            if existing is not None:
                return existing

        if source.platform != "youtube":
            raise CaseRadarReferenceError(
                "A promoção automática inicial suporta apenas YouTube; outras plataformas exigem source_type próprio"
            )

        video_id = self._youtube_video_id(source)
        reference = self.references.get_reference_source_by_youtube_video_id(video_id)
        if reference is None:
            engagement = source.engagement_json or {}
            reference = self.references.create_reference_source(
                ReferenceSourceCreate(
                    source_type="youtube_video",
                    source_url=source.canonical_url,
                    external_id=video_id,
                    youtube_video_id=video_id,
                    title=source.title_or_caption or f"YouTube {video_id}",
                    channel_title=source.author_display_name or source.author_handle,
                    description=source.text,
                    published_at=source.published_at,
                    duration_seconds=int(source.duration_seconds) if source.duration_seconds is not None else None,
                    view_count=int(engagement.get("views", 0)) if engagement.get("views") is not None else None,
                    like_count=int(engagement.get("likes", 0)) if engagement.get("likes") is not None else None,
                    thumbnail_url=source.thumbnail_url,
                    language=source.language,
                    status="new",
                    raw_json={
                        "case_radar_source_id": source.id,
                        "case_radar_discovery_method": source.discovery_method,
                    },
                )
            )

        source.reference_source_id = reference.id
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return reference

    def request_transcription(
        self,
        source_id: int,
        preset: str = "balanced",
        preferred_languages: list[str] | None = None,
    ) -> ReferenceImportJob:
        del preset  # YouTube reference import currently owns caption/audio strategy.
        reference = self.promote_to_reference(source_id)
        if reference.source_type != "youtube_video":
            raise CaseRadarReferenceError("Transcrição automática inicial suporta apenas referência YouTube")

        existing_jobs = self.references.list_import_jobs_by_source_id(reference.id)
        for job in existing_jobs:
            if job.status in {"queued", "running", "completed"}:
                return job

        languages = preferred_languages or ["pt", "pt-BR", "en", "es"]
        job = self.references.create_import_job(
            source_url=reference.source_url,
            preferred_languages=languages,
            method="yt_dlp_captions",
        )
        job.reference_source_id = reference.id
        self.references.save_import_job(job)
        return job

    def get_active_transcript_segments(self, source_id: int):
        reference = self.promote_to_reference(source_id)
        transcripts = self.references.list_transcripts_by_source(reference.id)
        active = next((transcript for transcript in transcripts if transcript.is_active), None)
        if active is None:
            return []
        return self.references.list_segments_by_transcript_id(active.id)
