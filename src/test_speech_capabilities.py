from src.services.speech_worker_protocol import WorkerCapabilities
from speech_worker.runtime import capabilities


def test_worker_capability_payload_exposes_runtime_readiness_without_secrets():
    payload = WorkerCapabilities(
        worker_id="worker-1",
        operations=["stt", "tts"],
        ffmpeg_available=True,
        whisperx_available=True,
        torch_available=True,
        cuda_available=False,
        stt_ready=True,
        diarization_ready=False,
        tts_engines=[{"id": "kokoro", "available": True, "reason": None}],
        compute_types=["int8", "float32"],
        output_formats=["wav", "mp3"],
        espeak_available=True,
        hf_access_present=True,
    ).as_dict()

    assert payload["operations"] == ["stt", "tts"]
    assert payload["compute_types"] == ["int8", "float32"]
    assert payload["output_formats"] == ["wav", "mp3"]
    assert payload["espeak_available"] is True
    assert payload["hf_access_present"] is True
    assert payload["tts_engines"][0]["id"] == "kokoro"
    serialized = repr(payload)
    assert "HF_TOKEN" not in serialized
    assert "secret-token-value" not in serialized


def test_detect_capabilities_keeps_engine_failure_reasons(monkeypatch):
    monkeypatch.setattr(capabilities.shutil, "which", lambda name: "/usr/bin/" + name if name in {"ffmpeg", "espeak-ng"} else None)
    monkeypatch.setattr(capabilities, "_module_available", lambda name: name in {"whisperx", "torch"})
    monkeypatch.setattr(capabilities, "_torch_details", lambda available: (False, None, None))
    monkeypatch.setattr(
        capabilities,
        "_tts_engine_states",
        lambda: [
            {"id": "kokoro", "available": True, "reason": None},
            {"id": "piper", "available": False, "reason": "modelo ausente"},
        ],
    )
    monkeypatch.setenv("HF_TOKEN", "secret-token-value")

    detected = capabilities.detect_capabilities("worker-x").as_dict()
    assert detected["operations"] == ["stt", "tts"]
    assert detected["tts_engines"][1]["reason"] == "modelo ausente"
    assert detected["hf_access_present"] is True
    assert detected["espeak_available"] is True
    assert "secret-token-value" not in repr(detected)
