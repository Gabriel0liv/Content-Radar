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


def _tts_engines() -> list[str]:
    try:
        from speech_worker.tts.registry import TTSRegistry
        return [item["id"] for item in TTSRegistry().list_engines() if item["available"]]
    except Exception:
        return []


def detect_capabilities(worker_id: str | None = None) -> WorkerCapabilities:
    resolved_worker_id = worker_id or os.getenv("SPEECH_WORKER_ID", "local-worker-1")
    ffmpeg_available = shutil.which("ffmpeg") is not None
    whisperx_available = _module_available("whisperx")
    torch_available = _module_available("torch")
    cuda_available, gpu_name, vram_mb = _torch_details(torch_available)
    stt_ready = ffmpeg_available and whisperx_available and torch_available
    diarization_ready = stt_ready and bool(os.getenv("HF_TOKEN"))
    tts_engines = _tts_engines()
    operations: list[str] = []
    if stt_ready:
        operations.append("stt")
    if tts_engines:
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
    )


def environment_summary() -> dict[str, str | bool | int | None]:
    capabilities = detect_capabilities()
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ffmpeg_available": capabilities.ffmpeg_available,
        "whisperx_available": capabilities.whisperx_available,
        "torch_available": capabilities.torch_available,
        "cuda_available": capabilities.cuda_available,
        "gpu_name": capabilities.gpu_name,
        "vram_mb": capabilities.vram_mb,
    }
