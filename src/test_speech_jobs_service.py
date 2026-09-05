from types import SimpleNamespace

import pytest

from src.schemas.speech_jobs import SpeechSttJobCreate
from src.services.speech_jobs_service import SpeechJobsService, SpeechReferenceNotFoundError


class FakeDb:
    def __init__(self, references=None):
        self.references = references or {}

    def get(self, model, key):
        return self.references.get(key)


class FakeRepo:
    def __init__(self):
        self.created = None

    def create(self, **kwargs):
        self.created = kwargs
        return SimpleNamespace(**kwargs, id=1, status="queued", stage="queued")

    def request_cancel(self, job_id):
        return None


def test_create_stt_job_resolves_preset_before_persisting():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    service.create_stt_job(SpeechSttJobCreate(preset="balanced", diarization=True, num_speakers=2))
    assert service.repo.created["requested_config_json"]["preset"] == "balanced"
    assert service.repo.created["resolved_config_json"]["model"] == "medium"
    assert service.repo.created["resolved_config_json"]["no_diarization"] is False
    assert service.repo.created["resolved_config_json"]["num_speakers"] == 2


def test_create_stt_job_rejects_unknown_reference():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    with pytest.raises(SpeechReferenceNotFoundError):
        service.create_stt_job(SpeechSttJobCreate(reference_source_id=999))


def test_cancel_missing_job_returns_none():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    assert service.cancel_job(999) is None
