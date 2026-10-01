from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from src.services.speech_jobs_service import SpeechJobsService
from src.services.speech_storage import SpeechStorage


class FakeRepo:
    def dashboard_counts(self, since):
        assert since.tzinfo is not None
        return {
            "total_jobs": 20,
            "jobs_completed": 15,
            "jobs_failed": 3,
            "transcriptions_today": 4,
            "tts_today": 6,
        }

    def list_recent(self, limit=50, **kwargs):
        assert limit == 6
        return [
            SimpleNamespace(
                id=9,
                operation="tts",
                status="completed",
                stage="completed",
                progress_percent=100,
                progress_message=None,
                error_code=None,
                error_message=None,
                created_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
                finished_at=datetime(2026, 10, 1, 12, 1, tzinfo=timezone.utc),
                requested_config_json={"text": "Olá mundo", "voice": "pt_br_dora"},
                resolved_config_json={"voice": "pt_br_dora"},
            )
        ]


class FakeAssets:
    def list_voices(self, *, capabilities=None):
        assert capabilities == {"tts_engines": [{"id": "kokoro", "available": True}]}
        return [
            {"id": "pt_br_dora", "available": True},
            {"id": "pt_br_faber", "available": False},
        ]


def test_dashboard_matches_legacy_useful_metrics_without_local_paths(tmp_path):
    storage = SpeechStorage(tmp_path)
    artifact = storage.root / "jobs" / "9" / "artifacts" / "voice.wav"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"123456")

    service = SpeechJobsService.__new__(SpeechJobsService)
    service.repo = FakeRepo()
    service.assets = FakeAssets()
    service.storage = storage
    service.get_status = lambda: {
        "mode": "native",
        "queue": {"queued": 2, "running": 1},
        "worker": {
            "online": True,
            "worker_id": "speech-1",
            "last_heartbeat_at": datetime.now(timezone.utc),
            "capabilities": {"tts_engines": [{"id": "kokoro", "available": True}]},
        },
    }

    dashboard = service.get_dashboard()

    assert dashboard["transcriptions_today"] == 4
    assert dashboard["tts_today"] == 6
    assert dashboard["total_jobs"] == 20
    assert dashboard["success_rate"] == 75.0
    assert dashboard["available_voices"] == 1
    assert dashboard["storage_used_bytes"] == 6
    assert dashboard["queue"] == {"queued": 2, "running": 1}
    assert dashboard["recent_jobs"][0]["id"] == 9
    assert dashboard["recent_jobs"][0]["label"] == "Olá mundo"
    assert "input_path" not in dashboard["recent_jobs"][0]
    assert "storage_key" not in str(dashboard)
