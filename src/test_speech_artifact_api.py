from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.speech_jobs import get_speech_jobs_service


client = TestClient(app)


def _artifact(path: Path, *, artifact_id: int = 4, job_id: int = 7):
    return SimpleNamespace(
        id=artifact_id,
        speech_job_id=job_id,
        artifact_type="audio",
        storage_key=f"jobs/{job_id}/artifacts/{path.name}",
        filename=path.name,
        mime_type="audio/wav",
        size_bytes=path.stat().st_size if path.exists() else None,
        created_at=datetime.now(timezone.utc),
    )


def test_download_artifact_returns_managed_file(tmp_path):
    target = tmp_path / "jobs" / "7" / "artifacts" / "speech.wav"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"RIFFaudio")
    artifact = _artifact(target)

    class FakeService:
        def resolve_artifact_download(self, job_id, artifact_id):
            assert (job_id, artifact_id) == (7, 4)
            return artifact, target

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/jobs/7/artifacts/4/download")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.content == b"RIFFaudio"
    assert response.headers["content-type"].startswith("audio/wav")


def test_download_missing_artifact_returns_404():
    class FakeService:
        def resolve_artifact_download(self, job_id, artifact_id):
            raise FileNotFoundError("Artefato não encontrado")

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/jobs/7/artifacts/999/download")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 404


def test_download_rejects_tampered_storage_path():
    class FakeService:
        def resolve_artifact_download(self, job_id, artifact_id):
            raise ValueError("Artefato aponta para fora do armazenamento permitido")

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/jobs/7/artifacts/4/download")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400
