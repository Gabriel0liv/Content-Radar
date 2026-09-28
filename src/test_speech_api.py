from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.speech_jobs import get_speech_jobs_service


client = TestClient(app)


def _job(**overrides):
    now = datetime.now(timezone.utc)
    data = {
        "id": 1,
        "operation": "stt",
        "status": "queued",
        "stage": "queued",
        "progress_percent": 0,
        "progress_message": None,
        "requested_config_json": {"preset": "fast"},
        "resolved_config_json": {"model": "small"},
        "reference_source_id": None,
        "transcript_id": None,
        "retry_of_job_id": None,
        "worker_id": None,
        "error_code": None,
        "error_message": None,
        "archived_at": None,
        "created_at": now,
        "started_at": None,
        "finished_at": None,
        "updated_at": now,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_stt_presets_expose_three_builtin_modes():
    response = client.get("/speech/stt/presets")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["presets"]]
    assert names == ["fast", "balanced", "max_quality"]


def test_resolve_endpoint_returns_technical_config():
    response = client.post(
        "/speech/stt/resolve",
        json={
            "preset": "balanced",
            "identify_speakers": True,
            "quiet_speech": True,
            "num_speakers": 2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolved"]["model"] == "medium"
    assert body["resolved"]["no_diarization"] is False
    assert body["resolved"]["num_speakers"] == 2
    assert body["resolved"]["vad_onset"] == 0.1


def test_native_status_stays_200_without_worker():
    class FakeService:
        def get_status(self):
            return {
                "mode": "native",
                "queue": {"queued": 0, "running": 0},
                "worker": {
                    "online": False,
                    "worker_id": None,
                    "last_heartbeat_at": None,
                    "capabilities": None,
                },
            }

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.get("/speech/status")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["mode"] == "native"
    assert response.json()["worker"]["online"] is False


def test_json_stt_job_requires_managed_upload():
    response = client.post("/speech/jobs/stt", json={"preset": "fast"})
    assert response.status_code == 400
    assert "upload" in response.json()["detail"].lower()


def test_create_stt_job_rejects_arbitrary_input_path():
    response = client.post(
        "/speech/jobs/stt",
        json={"preset": "fast", "input_path": "C:/Users/me/secret.wav"},
    )
    assert response.status_code == 422


def test_upload_stt_job_streams_file_to_managed_service():
    captured = {}

    class FakeService:
        def create_uploaded_stt_job(self, request, *, filename, chunks):
            captured["request"] = request
            captured["filename"] = filename
            captured["bytes"] = b"".join(chunks)
            return _job(requested_config_json=request.model_dump(exclude_none=True))

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.post(
            "/speech/jobs/stt/upload",
            data={"preset": "balanced", "diarization": "true", "num_speakers": "2"},
            files={"file": ("voice.wav", b"abc123", "audio/wav")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert captured["filename"] == "voice.wav"
    assert captured["bytes"] == b"abc123"
    assert captured["request"].diarization is True
    assert captured["request"].num_speakers == 2


def test_upload_stt_job_accepts_advanced_worker_options():
    captured = {}

    class FakeService:
        def create_uploaded_stt_job(self, request, *, filename, chunks):
            captured["request"] = request
            captured["bytes"] = b"".join(chunks)
            return _job(requested_config_json=request.model_dump(exclude_none=True))

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.post(
            "/speech/jobs/stt/upload",
            data={
                "preset": "balanced",
                "model": "large-v3",
                "device": "cuda",
                "compute_type": "float16",
                "batch_size": "1",
                "vad_onset": "0.15",
                "vad_offset": "0.2",
                "chunk_size": "45",
                "diarize_model": "pyannote/custom",
                "offline": "true",
                "cache_dir": "D:/models/hf",
                "export_formats": "txt,srt,vtt",
            },
            files={"file": ("voice.mp4", b"abc123", "video/mp4")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    request = captured["request"]
    assert request.model == "large-v3"
    assert request.device == "cuda"
    assert request.compute_type == "float16"
    assert request.batch_size == 1
    assert request.vad_onset == 0.15
    assert request.vad_offset == 0.2
    assert request.chunk_size == 45
    assert request.offline is True
    assert request.export_formats == ["txt", "srt", "vtt"]


def test_upload_stt_job_returns_422_for_invalid_speaker_range():
    response = client.post(
        "/speech/jobs/stt/upload",
        data={"preset": "balanced", "min_speakers": "4", "max_speakers": "2"},
        files={"file": ("voice.wav", b"abc123", "audio/wav")},
    )
    assert response.status_code == 422


def test_upload_stt_job_returns_400_for_unsupported_media_extension():
    class FakeService:
        def create_uploaded_stt_job(self, request, *, filename, chunks):
            raise ValueError("Formato de entrada não suportado")

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.post(
            "/speech/jobs/stt/upload",
            data={"preset": "balanced"},
            files={"file": ("notes.txt", b"abc123", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400


def test_create_tts_job_persists_durable_request():
    captured = {}

    class FakeService:
        def create_tts_job(self, request):
            captured["request"] = request
            return _job(
                operation="tts",
                requested_config_json=request.model_dump(exclude_none=True),
                resolved_config_json={"engine": request.engine, "voice": request.voice},
            )

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.post(
            "/speech/jobs/tts",
            json={
                "text": "Olá mundo",
                "engine": "kokoro",
                "voice": "pt_br_dora",
                "output_format": "wav",
                "speed": 1.05,
                "normalize_ptbr": True,
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert response.json()["operation"] == "tts"
    assert captured["request"].preview is False
    assert captured["request"].voice == "pt_br_dora"


def test_tts_preview_endpoint_forces_preview_mode():
    captured = {}

    class FakeService:
        def create_tts_job(self, request):
            captured["request"] = request
            return _job(
                operation="tts",
                requested_config_json=request.model_dump(exclude_none=True),
                resolved_config_json={"engine": request.engine, "voice": request.voice, "preview": request.preview},
            )

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.post(
            "/speech/jobs/tts/preview",
            json={"text": "Teste", "engine": "piper", "voice": "pt_br_faber", "preview": False},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 201
    assert captured["request"].preview is True


def test_tts_analysis_is_synchronous_and_advisory():
    response = client.post("/speech/tts/analyze-text", json={"text": "Ola voce"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["analysis"]["original_text"] == "Ola voce"
    assert body["analysis"]["normalized_text"] == "Ola voce"
    assert body["analysis"]["has_issues"] is True


def test_cancel_queued_job():
    class FakeService:
        def cancel_job(self, job_id):
            return _job(id=job_id, status="cancelled", stage="cancelled")

    app.dependency_overrides[get_speech_jobs_service] = lambda: FakeService()
    try:
        response = client.post("/speech/jobs/7/cancel")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["status"] == "cancelled"
