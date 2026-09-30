from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.services.speech_jobs_service import SpeechJobsService
from src.services.speech_storage import SpeechStorage


class FakeDb:
    def get(self, model, key):
        return None


class FakeRepo:
    def __init__(self, jobs=None, artifacts=None):
        self.jobs = jobs or {}
        self.artifacts = artifacts or {}
        self.archived = []
        self.retried = []
        self.deleted_artifacts = []

    def get(self, job_id):
        return self.jobs.get(job_id)

    def list_recent(self, limit, **filters):
        values = list(self.jobs.values())
        if filters.get("operation"):
            values = [job for job in values if job.operation == filters["operation"]]
        if filters.get("status"):
            values = [job for job in values if job.status == filters["status"]]
        return sorted(values, key=lambda job: (job.created_at, job.id), reverse=True)[:limit]

    def retry(self, job_id):
        self.retried.append(job_id)
        original = self.jobs.get(job_id)
        if original is None:
            return None
        return SimpleNamespace(id=99, retry_of_job_id=job_id, operation=original.operation, status="queued")

    def archive(self, job_id):
        self.archived.append(job_id)
        return self.jobs.get(job_id)

    def get_artifact(self, job_id, artifact_id):
        artifact = self.artifacts.get(artifact_id)
        if artifact is None or artifact.speech_job_id != job_id:
            return None
        return artifact

    def delete_artifact(self, artifact_id):
        self.deleted_artifacts.append(artifact_id)
        return self.artifacts.pop(artifact_id, None)


def _job(job_id, *, operation="stt", status="completed", transcript_id=None, created_at=None):
    return SimpleNamespace(
        id=job_id,
        operation=operation,
        status=status,
        stage=status,
        progress_percent=100 if status == "completed" else 25,
        progress_message="processando" if status == "running" else None,
        transcript_id=transcript_id,
        reference_source_id=None,
        requested_config_json={},
        resolved_config_json={},
        input_path=None,
        error_code="boom" if status == "failed" else None,
        error_message="falhou" if status == "failed" else None,
        created_at=created_at or datetime.now(timezone.utc),
    )


def test_history_is_newest_first_and_filterable(tmp_path):
    old = _job(1, operation="stt", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    new = _job(2, operation="tts", created_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    service = SpeechJobsService(FakeDb(), storage=SpeechStorage(tmp_path))
    service.repo = FakeRepo({1: old, 2: new})

    assert [job.id for job in service.list_jobs()] == [2, 1]
    assert [job.id for job in service.list_jobs(operation="tts")] == [2]


def test_retry_as_new_job_keeps_original_and_links_retry(tmp_path):
    original = _job(7, operation="tts", status="failed")
    service = SpeechJobsService(FakeDb(), storage=SpeechStorage(tmp_path))
    service.repo = FakeRepo({7: original})

    retried = service.retry_job(7)
    assert retried.retry_of_job_id == 7
    assert retried.status == "queued"
    assert original.status == "failed"


def test_archive_history_does_not_delete_linked_transcript(tmp_path):
    original = _job(7, transcript_id=42)
    service = SpeechJobsService(FakeDb(), storage=SpeechStorage(tmp_path))
    repo = FakeRepo({7: original})
    service.repo = repo

    archived = service.archive_job(7)
    assert archived.transcript_id == 42
    assert repo.archived == [7]


def test_delete_artifact_requires_explicit_action_and_never_deletes_transcript(tmp_path):
    path = tmp_path / "jobs" / "7" / "artifacts" / "transcript.srt"
    path.parent.mkdir(parents=True)
    path.write_text("subtitle", encoding="utf-8")
    job = _job(7, transcript_id=42)
    artifact = SimpleNamespace(
        id=3,
        speech_job_id=7,
        artifact_type="srt",
        storage_key="jobs/7/artifacts/transcript.srt",
        filename="transcript.srt",
    )
    service = SpeechJobsService(FakeDb(), storage=SpeechStorage(tmp_path))
    repo = FakeRepo({7: job}, {3: artifact})
    service.repo = repo

    removed = service.delete_artifact(7, 3)
    assert removed.id == 3
    assert not path.exists()
    assert job.transcript_id == 42
    assert repo.deleted_artifacts == [3]


def test_delete_artifact_rejects_path_escape(tmp_path):
    outside = tmp_path.parent / "secret.wav"
    outside.write_bytes(b"secret")
    artifact = SimpleNamespace(
        id=3,
        speech_job_id=7,
        artifact_type="audio",
        storage_key="../secret.wav",
        filename="secret.wav",
    )
    service = SpeechJobsService(FakeDb(), storage=SpeechStorage(tmp_path))
    service.repo = FakeRepo({7: _job(7)}, {3: artifact})

    with pytest.raises(ValueError):
        service.delete_artifact(7, 3)
    assert outside.exists()
