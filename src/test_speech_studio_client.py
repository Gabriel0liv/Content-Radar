import httpx
import pytest

from src.schemas.speech import ResolvedSpeechSttConfig
from src.services.speech_studio_client import (
    SpeechStudioBusyError,
    SpeechStudioClient,
)


def _config(**overrides):
    data = {
        "model": "medium",
        "language": "pt",
        "compute_type": "int8",
        "batch_size": 2,
        "no_diarization": False,
        "vad_onset": 0.5,
        "vad_offset": 0.363,
        "initial_prompt": "Hades, Poseidon",
    }
    data.update(overrides)
    return ResolvedSpeechSttConfig(**data)


def test_health_success_returns_online_status():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok"})

    client = SpeechStudioClient(
        base_url="http://speech.test",
        transport=httpx.MockTransport(handler),
    )
    status = client.health()
    assert status.online is True
    assert status.engine == "speech_studio"


def test_health_connection_error_is_normalized_as_offline():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = SpeechStudioClient(
        base_url="http://speech.test",
        transport=httpx.MockTransport(handler),
    )
    status = client.health()
    assert status.online is False
    assert "indisponível" in status.message.lower()


def test_transcribe_409_becomes_busy_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": "GPU busy"})

    client = SpeechStudioClient(
        base_url="http://speech.test",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(SpeechStudioBusyError):
        client.transcribe_file("audio.wav", b"abc", _config())


def test_transcribe_sends_resolved_form_and_omits_none_fields():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode("utf-8", errors="ignore")
        captured["body"] = body
        captured["content_type"] = request.headers.get("content-type", "")
        return httpx.Response(
            200,
            json={
                "success": True,
                "output_dir": "x",
                "artifacts": [],
                "stdout": "",
                "stderr": "",
                "returncode": 0,
                "logs": "",
                "error": None,
                "message": "Transcricao concluida.",
            },
        )

    client = SpeechStudioClient(
        base_url="http://speech.test",
        transport=httpx.MockTransport(handler),
    )
    result = client.transcribe_file(
        "audio.wav",
        b"abc",
        _config(num_speakers=2, min_speakers=None, max_speakers=None),
    )
    assert result.success is True
    assert "multipart/form-data" in captured["content_type"]
    assert 'name="model"' in captured["body"]
    assert "medium" in captured["body"]
    assert 'name="num_speakers"' in captured["body"]
    assert 'name="min_speakers"' not in captured["body"]
    assert 'name="initial_prompt"' in captured["body"]
