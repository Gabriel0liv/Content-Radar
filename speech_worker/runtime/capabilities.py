from __future__ import annotations

import os
import platform
import shutil

from src.services.speech_worker_protocol import WorkerCapabilities


def detect_capabilities(worker_id: str | None = None) -> WorkerCapabilities:
    resolved_worker_id = worker_id or os.getenv("SPEECH_WORKER_ID", "local-worker-1")
    return WorkerCapabilities(
        worker_id=resolved_worker_id,
        operations=[],
        cpu_available=True,
        cuda_available=False,
        gpu_name=None,
        vram_mb=None,
        stt_ready=False,
        diarization_ready=False,
        tts_engines=[],
    )


def environment_summary() -> dict[str, str | bool]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "ffmpeg_available": shutil.which("ffmpeg") is not None,
    }
