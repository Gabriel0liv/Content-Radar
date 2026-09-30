from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.speech_jobs import get_speech_jobs_service


client = TestClient(app)


def _job(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": 22,
        "operation": "stt",
        "status": "completed",
        "stage": "completed",
        "progress_percent": 100,
        "progress_message": None,
        "requested_config_json": {"preset": "fast"},
        "resolved_config_json": {"model": "small"},
        "result_json": {"kind": "stt", "normalized": {"full_text": "Olá", "segments": []}},
        "reference_source_id": None,
        "transcript_id": None,
        "retry_of_job_id": None,
        "worker_id": "worker-1",
        "error_code": None,
        "error_message": None,
        "archived_at": None,
        "created_at": now,
        "started_at": now,
        "finished_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_job_read_exposes_result_payload_needed_by_audio_workspace():
    class FakeService:
        def get_job(self, job_id):
            return _job(id=job_id)

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/jobs/22")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["result_json"]["normalized"]["full_text"] == "Olá"


def test_job_artifacts_can_be_listed_before_download():
    class FakeService:
        def list_artifacts(self, job_id):
            return [
                SimpleNamespace(
                    id=7,
                    speech_job_id=job_id,
                    artifact_type="srt",
                    filename="transcript.srt",
                    mime_type="application/x-subrip",
                    size_bytes=321,
                    created_at=datetime.now(timezone.utc),
                )
            ]

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/jobs/22/artifacts")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body[0]["id"] == 7
    assert body[0]["artifact_type"] == "srt"
    assert "storage_key" not in body[0]


def test_speaker_display_mapping_round_trip_contract():
    class FakeService:
        def list_speaker_mappings(self, job_id):
            return [SimpleNamespace(raw_speaker="SPEAKER_00", display_name="Gabriel")]

        def set_speaker_mapping(self, job_id, raw_speaker, display_name):
            return SimpleNamespace(raw_speaker=raw_speaker, display_name=display_name)

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/jobs/22/speaker-mappings")
        updated = client.put(
            "/speech/jobs/22/speaker-mappings/SPEAKER_00",
            json={"display_name": "Narrador"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0] == {"raw_speaker": "SPEAKER_00", "display_name": "Gabriel"}
    assert updated.status_code == 200
    assert updated.json() == {"raw_speaker": "SPEAKER_00", "display_name": "Narrador"}
