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


def test_advanced_stt_overrides_are_preserved_in_resolved_config():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    service.create_stt_job(SpeechSttJobCreate(
        preset="balanced",
        language="pt",
        diarization=True,
        model="large-v3",
        device="cuda",
        compute_type="float16",
        batch_size=1,
        vad_onset=0.15,
        vad_offset=0.2,
        chunk_size=45,
        diarize_model="pyannote/custom",
        offline=True,
        cache_dir="D:/models/hf",
        export_formats=["txt", "srt"],
        initial_prompt="Drathos, Hades, Neris",
    ))
    resolved = service.repo.created["resolved_config_json"]
    assert resolved["model"] == "large-v3"
    assert resolved["device"] == "cuda"
    assert resolved["compute_type"] == "float16"
    assert resolved["batch_size"] == 1
    assert resolved["vad_onset"] == 0.15
    assert resolved["vad_offset"] == 0.2
    assert resolved["chunk_size"] == 45
    assert resolved["diarize_model"] == "pyannote/custom"
    assert resolved["offline"] is True
    assert resolved["cache_dir"] == "D:/models/hf"
    assert resolved["export_formats"] == ["txt", "srt"]


def test_sensitive_quiet_speech_does_not_overwrite_explicit_vad_values():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    service.create_stt_job(SpeechSttJobCreate(
        preset="balanced",
        quiet_speech=True,
        vad_onset=0.22,
        vad_offset=0.25,
    ))
    resolved = service.repo.created["resolved_config_json"]
    assert resolved["vad_onset"] == 0.22
    assert resolved["vad_offset"] == 0.25


def test_invalid_advanced_stt_values_are_rejected_by_schema():
    with pytest.raises(Exception):
        SpeechSttJobCreate(batch_size=0)
    with pytest.raises(Exception):
        SpeechSttJobCreate(device="metal")
    with pytest.raises(Exception):
        SpeechSttJobCreate(vad_onset=1.5)
    with pytest.raises(Exception):
        SpeechSttJobCreate(export_formats=["exe"])


def test_create_stt_job_rejects_unknown_reference():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    with pytest.raises(SpeechReferenceNotFoundError):
        service.create_stt_job(SpeechSttJobCreate(reference_source_id=999))


def test_cancel_missing_job_returns_none():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    assert service.cancel_job(999) is None
