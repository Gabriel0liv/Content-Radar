from fastapi.testclient import TestClient

from src.api.main import app


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
            "num_speakers": 2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolved"]["model"] == "medium"
    assert body["resolved"]["no_diarization"] is False
    assert body["resolved"]["num_speakers"] == 2
    assert body["resolved"]["vad_onset"] == 0.1
