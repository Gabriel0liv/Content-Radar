from speech_worker.runtime.diagnostics import build_diagnostics


def _capabilities(**overrides):
    data = {
        "worker_id": "worker-1",
        "operations": ["stt", "tts"],
        "cpu_available": True,
        "ffmpeg_available": True,
        "whisperx_available": True,
        "torch_available": True,
        "cuda_available": False,
        "gpu_name": None,
        "vram_mb": None,
        "stt_ready": True,
        "diarization_ready": False,
        "tts_engines": [
            {"id": "kokoro", "available": True, "reason": None},
            {"id": "piper", "available": False, "reason": "modelo ausente"},
        ],
        "compute_types": ["int8", "float32"],
        "output_formats": ["wav", "mp3"],
        "espeak_available": True,
        "hf_access_present": False,
    }
    data.update(overrides)
    return data


def test_diagnostics_explain_missing_hf_access_without_exposing_token():
    result = build_diagnostics(_capabilities())
    by_id = {check["id"]: check for check in result["checks"]}
    assert by_id["hf_access"]["status"] == "warning"
    assert "diarização" in by_id["hf_access"]["reason"].lower()
    assert "token" not in by_id["hf_access"].get("value", "").lower()


def test_diagnostics_report_missing_ffmpeg_and_espeak_as_actionable_errors():
    result = build_diagnostics(_capabilities(ffmpeg_available=False, espeak_available=False, stt_ready=False, operations=[]))
    by_id = {check["id"]: check for check in result["checks"]}
    assert by_id["ffmpeg"]["status"] == "error"
    assert by_id["espeak"]["status"] == "error"
    assert by_id["ffmpeg"]["action"]
    assert by_id["espeak"]["action"]


def test_cpu_only_runtime_is_informational_not_failure():
    result = build_diagnostics(_capabilities(cuda_available=False))
    by_id = {check["id"]: check for check in result["checks"]}
    assert by_id["cuda"]["status"] == "info"
    assert "cpu" in by_id["cuda"]["reason"].lower()


def test_unavailable_tts_engine_keeps_normalized_reason():
    result = build_diagnostics(_capabilities())
    by_id = {check["id"]: check for check in result["checks"]}
    assert by_id["tts:piper"]["status"] == "warning"
    assert by_id["tts:piper"]["reason"] == "modelo ausente"
