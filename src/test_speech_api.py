from fastapi.testclient import TestClient

from src.api.main import app
from src.schemas.speech import SpeechEngineStatus


client = TestClient(app)


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
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolved"]["model"] == "medium"
    assert body["resolved"]["no_diarization"] is False
    assert body["resolved"]["vad_onset"] == 0.1


def test_status_endpoint_stays_200_when_engine_is_offline(monkeypatch):
    from src.api.routes import speech

    class FakeClient:
        def health(self):
            return SpeechEngineStatus(
                online=False,
                base_url="http://speech.test",
                message="Speech Studio indisponível",
            )

    monkeypatch.setattr(speech, "get_speech_studio_client", lambda: FakeClient())
    response = client.get("/speech/status")
    assert response.status_code == 200
    assert response.json()["online"] is False
