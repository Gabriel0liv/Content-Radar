from pathlib import Path
from types import SimpleNamespace

import pytest

from src.schemas.speech_jobs import SpeechTtsJobCreate
from src.services.speech_jobs_service import SpeechJobsService
from speech_worker.tts.runner import TTSRunner


class FakeDb:
    def get(self, model, key):
        return None


class FakeRepo:
    def __init__(self):
        self.created = None

    def create(self, **kwargs):
        self.created = kwargs
        return SimpleNamespace(id=9, status="queued", stage="queued", **kwargs)


class FakeEngine:
    def __init__(self):
        self.calls = []

    def synthesize(self, text, output_path, output_format="wav"):
        self.calls.append((text, str(output_path), output_format))
        Path(output_path).write_bytes(b"RIFFfake")
        return Path(output_path)


class FakeRegistry:
    def __init__(self, engine):
        self.engine = engine

    def create_engine(self, name, voice_id, **kwargs):
        return self.engine


def test_service_creates_durable_tts_job_with_text_and_resolved_config():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    job = service.create_tts_job(SpeechTtsJobCreate(
        text="Olá mundo",
        engine="kokoro",
        voice="pt_br_dora",
        output_format="wav",
        speed=1.1,
        normalize_ptbr=True,
    ))
    assert job.operation == "tts"
    assert service.repo.created["requested_config_json"]["text"] == "Olá mundo"
    assert service.repo.created["resolved_config_json"]["engine"] == "kokoro"
    assert service.repo.created["resolved_config_json"]["voice"] == "pt_br_dora"


def test_preview_job_limits_text_but_preserves_original_request():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    service.create_tts_job(SpeechTtsJobCreate(
        text="abcdefghij" * 50,
        engine="kokoro",
        voice="pt_br_dora",
        preview=True,
        preview_chars=30,
    ))
    requested = service.repo.created["requested_config_json"]
    resolved = service.repo.created["resolved_config_json"]
    assert len(requested["text"]) == 500
    assert len(resolved["effective_text"]) <= 30
    assert resolved["preview"] is True


def test_ptbr_normalization_changes_effective_text_only():
    service = SpeechJobsService(FakeDb())
    service.repo = FakeRepo()
    service.create_tts_job(SpeechTtsJobCreate(
        text="Ola voce",
        engine="kokoro",
        voice="pt_br_dora",
        normalize_ptbr=True,
    ))
    assert service.repo.created["requested_config_json"]["text"] == "Ola voce"
    assert service.repo.created["resolved_config_json"]["effective_text"] == "Olá você"


def test_runner_reports_chunk_progress_and_returns_managed_audio_artifact(tmp_path):
    from src.services.speech_storage import SpeechStorage

    engine = FakeEngine()
    runner = TTSRunner(storage=SpeechStorage(tmp_path), registry=FakeRegistry(engine))
    progress = []
    job = SimpleNamespace(
        id=4,
        resolved_config_json={
            "engine": "kokoro",
            "voice": "pt_br_dora",
            "effective_text": "Primeira frase. Segunda frase.",
            "output_format": "wav",
            "speed": 1.0,
            "device": "cpu",
            "chunk_chars": 20,
        },
    )
    result = runner.run(job, lambda stage, pct, msg: progress.append((stage, pct, msg)), lambda: False)
    assert result["kind"] == "tts"
    assert result["artifacts"][0]["artifact_type"] == "audio"
    assert result["artifacts"][0]["storage_key"].startswith("jobs/4/artifacts/")
    assert any(stage == "chunk" for stage, _, _ in progress)
    assert any(stage == "exporting" for stage, _, _ in progress)


def test_runner_checks_cancellation_between_chunks(tmp_path):
    from src.services.speech_storage import SpeechStorage
    from src.services.speech_worker_protocol import JobCancelled

    engine = FakeEngine()
    runner = TTSRunner(storage=SpeechStorage(tmp_path), registry=FakeRegistry(engine))
    checks = {"count": 0}

    def cancelled():
        checks["count"] += 1
        return checks["count"] >= 3

    job = SimpleNamespace(
        id=5,
        resolved_config_json={
            "engine": "kokoro",
            "voice": "pt_br_dora",
            "effective_text": "Uma frase. Outra frase. Mais uma frase.",
            "output_format": "wav",
            "speed": 1.0,
            "device": "cpu",
            "chunk_chars": 12,
        },
    )
    with pytest.raises(JobCancelled):
        runner.run(job, lambda *args: None, cancelled)


def test_analyze_ptbr_is_lightweight_and_does_not_create_job():
    from speech_worker.tts.ptbr_text import analyze_ptbr_text

    result = analyze_ptbr_text("Ola voce")
    assert result["has_issues"] is True
