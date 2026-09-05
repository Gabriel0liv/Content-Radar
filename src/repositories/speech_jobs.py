from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.speech import SpeechJob, SpeechWorkerState


class SpeechJobOwnershipError(RuntimeError):
    pass


class SpeechJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def create(
        self,
        operation: str,
        requested_config_json: dict,
        input_path: str | None = None,
        reference_source_id: int | None = None,
        resolved_config_json: dict | None = None,
    ) -> SpeechJob:
        job = SpeechJob(
            operation=operation,
            requested_config_json=requested_config_json,
            resolved_config_json=resolved_config_json,
            input_path=input_path,
            reference_source_id=reference_source_id,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get(self, job_id: int) -> SpeechJob | None:
        return self.db.get(SpeechJob, job_id)

    def list_recent(self, limit: int = 50) -> list[SpeechJob]:
        stmt = select(SpeechJob).order_by(SpeechJob.created_at.desc(), SpeechJob.id.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars())

    def request_cancel(self, job_id: int) -> SpeechJob | None:
        job = self.get(job_id)
        if job is None:
            return None
        now = self._now()
        if job.status == "queued":
            job.status = "cancelled"
            job.stage = "cancelled"
            job.finished_at = now
            job.cancel_requested_at = now
        elif job.status == "running" and job.cancel_requested_at is None:
            job.cancel_requested_at = now
        self.db.commit()
        self.db.refresh(job)
        return job

    def claim_next(
        self,
        worker_id: str,
        lease_seconds: int,
        operations: Iterable[str] = ("stt", "tts"),
    ) -> SpeechJob | None:
        now = self._now()
        stmt = (
            select(SpeechJob)
            .where(SpeechJob.status == "queued", SpeechJob.operation.in_(tuple(operations)))
            .order_by(SpeechJob.created_at, SpeechJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = self.db.execute(stmt).scalar_one_or_none()
        if job is None:
            self.db.rollback()
            return None
        job.status = "running"
        job.stage = "starting"
        job.worker_id = worker_id
        job.started_at = job.started_at or now
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        self.db.commit()
        self.db.refresh(job)
        return job

    def heartbeat(
        self,
        job_id: int,
        worker_id: str,
        lease_seconds: int,
        stage: str | None = None,
        progress_percent: int | None = None,
        progress_message: str | None = None,
    ) -> SpeechJob:
        job = self._owned_running(job_id, worker_id)
        now = self._now()
        job.heartbeat_at = now
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
        if stage is not None:
            job.stage = stage
        if progress_percent is not None:
            job.progress_percent = max(0, min(100, int(progress_percent)))
        if progress_message is not None:
            job.progress_message = progress_message
        self.db.commit()
        self.db.refresh(job)
        return job

    def complete(self, job_id: int, worker_id: str, result_json: dict) -> SpeechJob:
        job = self._owned_running(job_id, worker_id)
        now = self._now()
        job.status = "completed"
        job.stage = "completed"
        job.progress_percent = 100
        job.result_json = result_json
        job.finished_at = now
        job.lease_expires_at = None
        self.db.commit()
        self.db.refresh(job)
        return job

    def fail(self, job_id: int, worker_id: str, error_code: str, error_message: str) -> SpeechJob:
        job = self._owned_running(job_id, worker_id)
        job.status = "failed"
        job.stage = "failed"
        job.error_code = error_code
        job.error_message = error_message
        job.finished_at = self._now()
        job.lease_expires_at = None
        self.db.commit()
        self.db.refresh(job)
        return job

    def mark_cancelled(self, job_id: int, worker_id: str) -> SpeechJob:
        job = self._owned_running(job_id, worker_id)
        now = self._now()
        job.status = "cancelled"
        job.stage = "cancelled"
        job.cancel_requested_at = job.cancel_requested_at or now
        job.finished_at = now
        job.lease_expires_at = None
        self.db.commit()
        self.db.refresh(job)
        return job

    def recover_stale_leases(self, now: datetime | None = None) -> int:
        now = now or self._now()
        stmt = select(SpeechJob).where(
            SpeechJob.status == "running",
            SpeechJob.lease_expires_at.is_not(None),
            SpeechJob.lease_expires_at < now,
        )
        jobs = list(self.db.execute(stmt).scalars())
        for job in jobs:
            if job.cancel_requested_at is not None:
                job.status = "cancelled"
                job.stage = "cancelled"
                job.finished_at = now
            else:
                job.status = "queued"
                job.stage = "queued"
            job.worker_id = None
            job.lease_expires_at = None
            job.heartbeat_at = None
        if jobs:
            self.db.commit()
        return len(jobs)

    def upsert_worker_state(self, worker_id: str, capabilities_json: dict) -> SpeechWorkerState:
        now = self._now()
        state = self.db.get(SpeechWorkerState, worker_id)
        if state is None:
            state = SpeechWorkerState(
                worker_id=worker_id,
                capabilities_json=capabilities_json,
                last_heartbeat_at=now,
                started_at=now,
            )
            self.db.add(state)
        else:
            state.capabilities_json = capabilities_json
            state.last_heartbeat_at = now
        self.db.commit()
        self.db.refresh(state)
        return state

    def latest_worker_state(self) -> SpeechWorkerState | None:
        stmt = select(SpeechWorkerState).order_by(SpeechWorkerState.last_heartbeat_at.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def queue_counts(self) -> dict[str, int]:
        rows = self.db.execute(
            select(SpeechJob.status, func.count(SpeechJob.id))
            .where(SpeechJob.status.in_(("queued", "running")))
            .group_by(SpeechJob.status)
        ).all()
        counts = {"queued": 0, "running": 0}
        for status, count in rows:
            counts[status] = int(count)
        return counts

    def _owned_running(self, job_id: int, worker_id: str) -> SpeechJob:
        job = self.get(job_id)
        if job is None or job.status != "running" or job.worker_id != worker_id:
            raise SpeechJobOwnershipError("Job não pertence ao worker informado")
        return job
