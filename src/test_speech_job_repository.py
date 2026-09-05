from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from src.repositories.speech_jobs import SpeechJobOwnershipError, SpeechJobRepository


class ScalarResult:
    def __init__(self, one=None, many=None):
        self.one = one
        self.many = many or ([] if one is None else [one])

    def scalar_one_or_none(self):
        return self.one

    def scalars(self):
        return iter(self.many)


class FakeSession:
    def __init__(self, result=None, jobs=None):
        self.result = result or ScalarResult()
        self.jobs = jobs or {}
        self.last_stmt = None
        self.commits = 0
        self.rollbacks = 0

    def execute(self, stmt):
        self.last_stmt = stmt
        return self.result

    def get(self, model, key):
        return self.jobs.get(key)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, obj):
        return None

    def add(self, obj):
        self.jobs[getattr(obj, "id", len(self.jobs) + 1)] = obj


def _queued_job(job_id=1):
    return SimpleNamespace(
        id=job_id,
        operation="stt",
        status="queued",
        stage="queued",
        progress_percent=0,
        worker_id=None,
        started_at=None,
        heartbeat_at=None,
        lease_expires_at=None,
        cancel_requested_at=None,
        finished_at=None,
        result_json=None,
        error_code=None,
        error_message=None,
    )


def test_claim_next_marks_job_running_sets_lease_and_uses_skip_locked():
    job = _queued_job()
    session = FakeSession(result=ScalarResult(one=job), jobs={1: job})
    repo = SpeechJobRepository(session)
    claimed = repo.claim_next("worker-a", 120, operations=("stt",))
    assert claimed.status == "running"
    assert claimed.worker_id == "worker-a"
    assert claimed.lease_expires_at > claimed.heartbeat_at
    assert session.last_stmt._for_update_arg.skip_locked is True


def test_heartbeat_extends_owned_lease_and_clamps_progress():
    job = _queued_job()
    job.status = "running"
    job.worker_id = "worker-a"
    session = FakeSession(jobs={1: job})
    repo = SpeechJobRepository(session)
    updated = repo.heartbeat(1, "worker-a", 120, stage="transcribing", progress_percent=150)
    assert updated.stage == "transcribing"
    assert updated.progress_percent == 100


def test_wrong_worker_cannot_complete_job():
    job = _queued_job()
    job.status = "running"
    job.worker_id = "worker-a"
    repo = SpeechJobRepository(FakeSession(jobs={1: job}))
    with pytest.raises(SpeechJobOwnershipError):
        repo.complete(1, "worker-b", {"ok": True})


def test_recover_stale_running_job_requeues_it():
    now = datetime.now(timezone.utc)
    job = _queued_job()
    job.status = "running"
    job.stage = "transcribing"
    job.worker_id = "worker-a"
    job.heartbeat_at = now - timedelta(minutes=5)
    job.lease_expires_at = now - timedelta(seconds=1)
    session = FakeSession(result=ScalarResult(many=[job]), jobs={1: job})
    repo = SpeechJobRepository(session)
    assert repo.recover_stale_leases(now=now) == 1
    assert job.status == "queued"
    assert job.worker_id is None


def test_cancel_queued_job_becomes_cancelled():
    job = _queued_job()
    repo = SpeechJobRepository(FakeSession(jobs={1: job}))
    updated = repo.request_cancel(1)
    assert updated.status == "cancelled"
    assert updated.cancel_requested_at is not None
