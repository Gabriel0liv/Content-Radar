from __future__ import annotations

import importlib.util
import os
import platform
import shutil

from src.services.speech_worker_protocol import WorkerCapabilities


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _torch_details(torch_available: bool) -> tuple[bool, str | None, int | None]:
    if not torch_available:
        return False, None, None
    try:
        import torch  # type: ignore

        if not torch.cuda.is_available():
            return False, None, None
        gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        return True, gpu_name, int(props.total_memory / (1024 * 1024))
    except Exception:
        return False, None, None


def _tts_engine_states() -> list[dict[str, object]]:
    try:
        from speech_worker.tts.registry import TTSRegistry

        return [
            {
                "id": str(item["id"]),
                "available": bool(item.get("available")),
                "reason": item.get("reason"),
            }
            for item in TTSRegistry().list_engines()
        ]
    except Exception as exc:
        return [
            {
                "id": "tts_runtime",
                "available": False,
                "reason": f"Falha ao inspecionar motores TTS: {type(exc).__name__}",
            }
        ]


def _compute_types(torch_available: bool, cuda_available: bool) -> list[str]:
    if not torch_available:
        return []
    if cuda_available:
        return ["int8", "float16", "float32"]
    return ["int8", "float32"]


def detect_capabilities(worker_id: str | None = None) -> WorkerCapabilities:
    resolved_worker_id = worker_id or os.getenv("SPEECH_WORKER_ID", "local-worker-1")
    ffmpeg_available = shutil.which("ffmpeg") is not None
    espeak_available = shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None
    whisperx_available = _module_available("whisperx")
    torch_available = _module_available("torch")
    cuda_available, gpu_name, vram_mb = _torch_details(torch_available)
    stt_ready = ffmpeg_available and whisperx_available and torch_available
    hf_access_present = bool(os.getenv("HF_TOKEN"))
    diarization_ready = stt_ready and hf_access_present
    tts_engines = _tts_engine_states()
    tts_ready = any(bool(item.get("available")) for item in tts_engines)

    operations: list[str] = []
    if stt_ready:
        operations.append("stt")
    if tts_ready:
        operations.append("tts")

    return WorkerCapabilities(
        worker_id=resolved_worker_id,
        operations=operations,
        cpu_available=True,
        ffmpeg_available=ffmpeg_available,
        whisperx_available=whisperx_available,
        torch_available=torch_available,
        cuda_available=cuda_available,
        gpu_name=gpu_name,
        vram_mb=vram_mb,
        stt_ready=stt_ready,
        diarization_ready=diarization_ready,
        tts_engines=tts_engines,
        compute_types=_compute_types(torch_available, cuda_available),
        output_formats=["wav", "mp3"] if ffmpeg_available else ["wav"],
        espeak_available=espeak_available,
        hf_access_present=hf_access_present,
    )


def environment_summary() -> dict[str, str | bool | int | None | list[str]]:
    capabilities = detect_capabilities()
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ffmpeg_available": capabilities.ffmpeg_available,
        "espeak_available": capabilities.espeak_available,
        "whisperx_available": capabilities.whisperx_available,
        "torch_available": capabilities.torch_available,
        "cuda_available": capabilities.cuda_available,
        "gpu_name": capabilities.gpu_name,
        "vram_mb": capabilities.vram_mb,
        "compute_types": capabilities.compute_types,
        "output_formats": capabilities.output_formats,
    }
