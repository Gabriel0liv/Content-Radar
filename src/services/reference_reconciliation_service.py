from dataclasses import dataclass, field
from typing import Iterable, List

from sqlalchemy.orm import Session

from src.models.reference import ReferenceImportJob, ReferenceSource, Transcript


@dataclass
class ReconciliationConflict:
    youtube_video_id: str
    source_ids: List[int]
    reason: str


@dataclass
class ReconciliationReport:
    groups_found: int = 0
    groups_reconciled: int = 0
    sources_merged: int = 0
    transcripts_moved: int = 0
    jobs_moved: int = 0
    conflicts: List[ReconciliationConflict] = field(default_factory=list)


def choose_canonical_source(sources: Iterable[ReferenceSource]) -> ReferenceSource:
    candidates = list(sources)
    if not candidates:
        raise ValueError("Nenhuma fonte fornecida para reconciliação")

    def score(source: ReferenceSource):
        transcripts = list(getattr(source, "transcripts", []) or [])
        active_count = sum(1 for transcript in transcripts if getattr(transcript, "is_active", False))
        return (-int(active_count > 0), -len(transcripts), source.id)

    return sorted(candidates, key=score)[0]


class ReferenceReconciliationService:
    def __init__(self, db: Session):
        self.db = db

    def find_duplicate_groups(self):
        rows = (
            self.db.query(ReferenceSource.youtube_video_id)
            .filter(
                ReferenceSource.source_type == "youtube_video",
                ReferenceSource.youtube_video_id.isnot(None),
            )
            .group_by(ReferenceSource.youtube_video_id)
            .having(__import__("sqlalchemy").func.count(ReferenceSource.id) > 1)
            .all()
        )
        return [row[0] for row in rows]

    def reconcile(self, dry_run: bool = True) -> ReconciliationReport:
        report = ReconciliationReport()
        for video_id in self.find_duplicate_groups():
            report.groups_found += 1
            sources = (
                self.db.query(ReferenceSource)
                .filter(
                    ReferenceSource.source_type == "youtube_video",
                    ReferenceSource.youtube_video_id == video_id,
                )
                .order_by(ReferenceSource.id.asc())
                .all()
            )
            canonical = choose_canonical_source(sources)
            duplicates = [source for source in sources if source.id != canonical.id]

            active_sources = [
                source.id
                for source in sources
                if any(transcript.is_active for transcript in source.transcripts)
            ]
            if len(active_sources) > 1:
                report.conflicts.append(
                    ReconciliationConflict(
                        youtube_video_id=video_id,
                        source_ids=[source.id for source in sources],
                        reason="Mais de uma fonte duplicada possui transcrição ativa; requer revisão manual.",
                    )
                )
                continue

            moved_transcripts = sum(len(source.transcripts) for source in duplicates)
            moved_jobs = sum(len(source.import_jobs) for source in duplicates)

            if not dry_run:
                for duplicate in duplicates:
                    self.db.query(Transcript).filter(
                        Transcript.reference_source_id == duplicate.id
                    ).update({Transcript.reference_source_id: canonical.id}, synchronize_session=False)
                    self.db.query(ReferenceImportJob).filter(
                        ReferenceImportJob.reference_source_id == duplicate.id
                    ).update({ReferenceImportJob.reference_source_id: canonical.id}, synchronize_session=False)
                    self.db.delete(duplicate)
                self.db.commit()

            report.groups_reconciled += 1
            report.sources_merged += len(duplicates)
            report.transcripts_moved += moved_transcripts
            report.jobs_moved += moved_jobs

        return report
