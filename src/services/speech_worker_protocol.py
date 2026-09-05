from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


class JobCancelled(RuntimeError):
    pass


class UnsupportedOperationError(RuntimeError):
    pass


@dataclass(slots=True)
class WorkerCapabilities:
    worker_id: str
    operations: list[str] = field(default_factory=lambda: ["stt", "tts"])
    cpu_available: bool = True
    cuda_available: bool = False
    gpu_name: str | None = None
    vram_mb: int | None = None
    stt_ready: bool = False
    diarization_ready: bool = False
    tts_engines: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "operations": list(self.operations),
            "cpu_available": self.cpu_available,
            "cuda_available": self.cuda_available,
            "gpu_name": self.gpu_name,
            "vram_mb": self.vram_mb,
            "stt_ready": self.stt_ready,
            "diarization_ready": self.diarization_ready,
            "tts_engines": list(self.tts_engines),
        }


def clamp_progress(value: int | float) -> int:
    return max(0, min(100, int(value)))
