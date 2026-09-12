from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.case_radar.types import Candidate
from src.models.case_radar import (
    CaseClaim,
    CaseEvidence,
    CaseResearchQuery,
    CaseResearchRun,
    CaseSource,
    ResearchCase,
    ResearchSource,
    SocialContextItem,
)


class CaseResearchOwnershipError(RuntimeError):
    pass


class CaseRadarRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def create_run(self, request_json: dict[str, Any]) -> CaseResearchRun:
        run = CaseResearchRun(request_json=request_json)
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: int) -> CaseResearchRun | None:
        return self.db.get(CaseResearchRun, run_id)

    def list_runs(self, limit: int = 50, offset: int = 0) -> tuple[list[CaseResearchRun], int]:
        total = int(self.db.execute(select(func.count(CaseResearchRun.id))).scalar_one())
        rows = list(
            self.db.execute(
                select(CaseResearchRun)
                .order_by(CaseResearchRun.created_at.desc(), CaseResearchRun.id.desc())
                .limit(max(1, min(200, limit)))
                .offset(max(0, offset))
            ).scalars()
        )
        return rows, total

    def list_queries(self, run_id: int) -> list[CaseResearchQuery]:
        return list(
            self.db.execute(
                select(CaseResearchQuery)
                .where(CaseResearchQuery.run_id == run_id)
                .order_by(CaseResearchQuery.id)
            ).scalars()
        )

    def list_sources(self, run_id: int) -> list[ResearchSource]:
        return list(
            self.db.execute(
                select(ResearchSource)
                .where(ResearchSource.run_id == run_id)
                .order_by(ResearchSource.id)
            ).scalars()
        )

    def list_cases(self, run_id: int) -> list[ResearchCase]:
        return list(
            self.db.execute(
                select(ResearchCase)
                .where(ResearchCase.run_id == run_id)
                .order_by(ResearchCase.id)
            ).scalars()
        )

    def get_case(self, case_id: int) -> ResearchCase | None:
        return self.db.get(ResearchCase, case_id)

    def request_cancel(self, run_id: int) -> CaseResearchRun | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        now = self._now()
        if run.status == "queued":
            run.status = "cancelled"
            run.stage = "cancelled"
            run.progress_message = "Pesquisa cancelada antes de iniciar"
            run.cancel_requested_at = now
            run.finished_at = now
            run.lease_expires_at = None
        elif run.status == "running" and run.cancel_requested_at is None:
            run.cancel_requested_at = now
        self.db.commit()
        self.db.refresh(run)
        return run

    def claim_next(self, worker_id: str, lease_seconds: int) -> CaseResearchRun | None:
        now = self._now()
        stmt = (
            select(CaseResearchRun)
            .where(CaseResearchRun.status == "queued")
            .order_by(CaseResearchRun.created_at, CaseResearchRun.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        run = self.db.execute(stmt).scalar_one_or_none()
        if run is None:
            self.db.rollback()
            return None
        run.status = "running"
        if run.stage == "queued":
            run.stage = "generating_queries"
        run.worker_id = worker_id
        run.started_at = run.started_at or now
        run.heartbeat_at = now
        run.lease_expires_at = now + timedelta(seconds=max(1, lease_seconds))
        self.db.commit()
        self.db.refresh(run)
        return run

    def heartbeat(
        self,
        run_id: int,
        worker_id: str,
        lease_seconds: int,
        *,
        stage: str,
        progress_percent: int,
        message: str | None = None,
    ) -> CaseResearchRun:
        run = self._owned_running(run_id, worker_id)
        now = self._now()
        run.heartbeat_at = now
        run.lease_expires_at = now + timedelta(seconds=max(1, lease_seconds))
        run.stage = stage
        run.progress_percent = max(0, min(100, int(progress_percent)))
        if message is not None:
            run.progress_message = message
        self.db.commit()
        self.db.refresh(run)
        return run

    def recover_stale_leases(self, now: datetime | None = None) -> int:
        now = now or self._now()
        runs = list(
            self.db.execute(
                select(CaseResearchRun).where(
                    CaseResearchRun.status == "running",
                    CaseResearchRun.lease_expires_at.is_not(None),
                    CaseResearchRun.lease_expires_at < now,
                )
            ).scalars()
        )
        for run in runs:
            if run.cancel_requested_at is not None:
                run.status = "cancelled"
                run.stage = "cancelled"
                run.finished_at = now
            else:
                run.status = "queued"
                if run.stage in {"completed", "partially_completed", "failed", "cancelled"}:
                    run.stage = "queued"
            run.worker_id = None
            run.heartbeat_at = None
            run.lease_expires_at = None
        if runs:
            self.db.commit()
        return len(runs)

    def complete(
        self,
        run_id: int,
        worker_id: str,
        *,
        partial: bool,
        summary: dict[str, Any],
    ) -> CaseResearchRun:
        run = self._owned_running(run_id, worker_id)
        now = self._now()
        terminal = "partially_completed" if partial else "completed"
        run.status = terminal
        run.stage = terminal
        run.progress_percent = 100
        run.result_summary_json = summary
        run.finished_at = now
        run.lease_expires_at = None
        run.heartbeat_at = now
        self.db.commit()
        self.db.refresh(run)
        return run

    def fail(
        self,
        run_id: int,
        worker_id: str,
        error_code: str,
        error_message: str,
    ) -> CaseResearchRun:
        run = self._owned_running(run_id, worker_id)
        now = self._now()
        errors = list(run.errors_json or [])
        errors.append({"code": error_code, "message": error_message, "at": now.isoformat()})
        run.errors_json = errors
        run.status = "failed"
        run.stage = "failed"
        run.progress_message = error_message
        run.finished_at = now
        run.lease_expires_at = None
        run.heartbeat_at = now
        self.db.commit()
        self.db.refresh(run)
        return run

    def upsert_query(
        self,
        *,
        run_id: int,
        language: str,
        target_platform: str | None,
        query_text: str,
        intent: str,
        status: str = "queued",
    ) -> CaseResearchQuery:
        stmt = select(CaseResearchQuery).where(
            CaseResearchQuery.run_id == run_id,
            CaseResearchQuery.language == language,
            CaseResearchQuery.intent == intent,
            CaseResearchQuery.query_text == query_text,
        )
        if target_platform is None:
            stmt = stmt.where(CaseResearchQuery.target_platform.is_(None))
        else:
            stmt = stmt.where(CaseResearchQuery.target_platform == target_platform)
        query = self.db.execute(stmt).scalar_one_or_none()
        if query is None:
            query = CaseResearchQuery(
                run_id=run_id,
                language=language,
                target_platform=target_platform,
                query_text=query_text,
                intent=intent,
                status=status,
            )
            self.db.add(query)
        else:
            query.status = status
        self.db.commit()
        self.db.refresh(query)
        return query

    def upsert_source(self, candidate: Candidate, run_id: int, query_id: int | None) -> ResearchSource:
        stmt = select(ResearchSource).where(ResearchSource.run_id == run_id)
        if candidate.external_id:
            stmt = stmt.where(
                ResearchSource.platform == candidate.platform,
                ResearchSource.external_id == candidate.external_id,
            )
        else:
            stmt = stmt.where(ResearchSource.canonical_url == candidate.canonical_url)
        source = self.db.execute(stmt).scalar_one_or_none()

        values = {
            "query_id": query_id,
            "platform": candidate.platform,
            "external_id": candidate.external_id,
            "canonical_url": candidate.canonical_url,
            "author_handle": candidate.author_handle,
            "author_display_name": candidate.author_display_name,
            "title_or_caption": candidate.title_or_caption,
            "text": candidate.text,
            "published_at": candidate.published_at,
            "media_type": candidate.media_type,
            "thumbnail_url": candidate.thumbnail_url,
            "duration_seconds": candidate.duration_seconds,
            "language": candidate.language,
            "engagement_json": candidate.engagement,
            "hashtags_json": candidate.hashtags,
            "relation_json": candidate.relation,
            "discovery_method": candidate.discovery_method,
            "raw_json": candidate.raw_json,
            "source_confidence": candidate.source_confidence,
        }
        if source is None:
            source = ResearchSource(run_id=run_id, **values)
            self.db.add(source)
        else:
            for key, value in values.items():
                setattr(source, key, value)
        self.db.commit()
        self.db.refresh(source)
        return source

    def create_social_item(
        self,
        *,
        source_id: int,
        platform_item_id: str | None,
        body: str,
        parent_social_context_id: int | None = None,
        **values: Any,
    ) -> SocialContextItem:
        existing = None
        if platform_item_id:
            existing = self.db.execute(
                select(SocialContextItem).where(
                    SocialContextItem.source_id == source_id,
                    SocialContextItem.platform_item_id == platform_item_id,
                )
            ).scalar_one_or_none()
        if existing is not None:
            for key, value in values.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            if existing.body != body:
                existing.body = body
            if existing.parent_social_context_id != parent_social_context_id:
                existing.parent_social_context_id = parent_social_context_id
            self.db.commit()
            self.db.refresh(existing)
            return existing
        item = SocialContextItem(
            source_id=source_id,
            platform_item_id=platform_item_id,
            parent_social_context_id=parent_social_context_id,
            body=body,
            **values,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def create_case(self, *, run_id: int, provisional_title: str, **values: Any) -> ResearchCase:
        case = ResearchCase(run_id=run_id, provisional_title=provisional_title, **values)
        self.db.add(case)
        self.db.commit()
        self.db.refresh(case)
        return case

    def link_case_source(
        self,
        *,
        case_id: int,
        source_id: int,
        role: str = "unknown",
        provenance_confidence: float = 0.0,
        reason: str | None = None,
        evidence_json: dict[str, Any] | None = None,
    ) -> CaseSource:
        link = self.db.execute(
            select(CaseSource).where(CaseSource.case_id == case_id, CaseSource.source_id == source_id)
        ).scalar_one_or_none()
        if link is None:
            link = CaseSource(case_id=case_id, source_id=source_id)
            self.db.add(link)
        link.role = role
        link.provenance_confidence = max(0.0, min(1.0, float(provenance_confidence)))
        link.reason = reason
        link.evidence_json = evidence_json or {}
        self.db.commit()
        self.db.refresh(link)
        return link

    def upsert_claim(
        self,
        *,
        case_id: int,
        normalized_claim_text: str,
        claim_type: str,
        status: str = "unverified",
        confidence: float = 0.0,
        entities_json: dict[str, Any] | None = None,
        extracted_date: datetime | None = None,
        extracted_location: str | None = None,
    ) -> CaseClaim:
        normalized = " ".join(normalized_claim_text.split())
        claim = self.db.execute(
            select(CaseClaim).where(
                CaseClaim.case_id == case_id,
                CaseClaim.normalized_claim_text == normalized,
                CaseClaim.claim_type == claim_type,
            )
        ).scalar_one_or_none()
        if claim is None:
            claim = CaseClaim(
                case_id=case_id,
                normalized_claim_text=normalized,
                claim_type=claim_type,
            )
            self.db.add(claim)
        claim.status = status
        claim.confidence = max(0.0, min(1.0, float(confidence)))
        claim.entities_json = entities_json or {}
        claim.extracted_date = extracted_date
        claim.extracted_location = extracted_location
        self.db.commit()
        self.db.refresh(claim)
        return claim

    def link_evidence(
        self,
        *,
        claim_id: int,
        stance: str,
        source_id: int | None = None,
        social_context_item_id: int | None = None,
        transcript_segment_id: int | None = None,
        note: str | None = None,
    ) -> CaseEvidence:
        if source_id is None and social_context_item_id is None and transcript_segment_id is None:
            raise ValueError("CaseEvidence exige ao menos um alvo")
        stmt = select(CaseEvidence).where(
            CaseEvidence.claim_id == claim_id,
            CaseEvidence.stance == stance,
        )
        if source_id is None:
            stmt = stmt.where(CaseEvidence.source_id.is_(None))
        else:
            stmt = stmt.where(CaseEvidence.source_id == source_id)
        if social_context_item_id is None:
            stmt = stmt.where(CaseEvidence.social_context_item_id.is_(None))
        else:
            stmt = stmt.where(CaseEvidence.social_context_item_id == social_context_item_id)
        if transcript_segment_id is None:
            stmt = stmt.where(CaseEvidence.transcript_segment_id.is_(None))
        else:
            stmt = stmt.where(CaseEvidence.transcript_segment_id == transcript_segment_id)
        evidence = self.db.execute(stmt).scalar_one_or_none()
        if evidence is None:
            evidence = CaseEvidence(
                claim_id=claim_id,
                source_id=source_id,
                social_context_item_id=social_context_item_id,
                transcript_segment_id=transcript_segment_id,
                stance=stance,
                note=note,
            )
            self.db.add(evidence)
        elif note is not None:
            evidence.note = note
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def _owned_running(self, run_id: int, worker_id: str) -> CaseResearchRun:
        run = self.get_run(run_id)
        if run is None or run.status != "running" or run.worker_id != worker_id:
            raise CaseResearchOwnershipError("Run do Case Radar não pertence ao worker informado")
        return run
