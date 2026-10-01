from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class JobCancelled(RuntimeError):
    pass


class UnsupportedOperationError(RuntimeError):
    pass


@dataclass(slots=True)
class WorkerCapabilities:
    worker_id: str
    operations: list[str] = field(default_factory=list)
    cpu_available: bool = True
    ffmpeg_available: bool = False
    whisperx_available: bool = False
    torch_available: bool = False
    cuda_available: bool = False
    gpu_name: str | None = None
    vram_mb: int | None = None
    stt_ready: bool = False
    diarization_ready: bool = False
    tts_engines: list[Any] = field(default_factory=list)
    compute_types: list[str] = field(default_factory=list)
    output_formats: list[str] = field(default_factory=list)
    espeak_available: bool = False
    hf_access_present: bool = False

    def as_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "operations": list(self.operations),
            "cpu_available": self.cpu_available,
            "ffmpeg_available": self.ffmpeg_available,
            "whisperx_available": self.whisperx_available,
            "torch_available": self.torch_available,
            "cuda_available": self.cuda_available,
            "gpu_name": self.gpu_name,
            "vram_mb": self.vram_mb,
            "stt_ready": self.stt_ready,
            "diarization_ready": self.diarization_ready,
            "tts_engines": [dict(item) if isinstance(item, dict) else item for item in self.tts_engines],
            "compute_types": list(self.compute_types),
            "output_formats": list(self.output_formats),
            "espeak_available": self.espeak_available,
            "hf_access_present": self.hf_access_present,
        }


def clamp_progress(value: int | float) -> int:
    return max(0, min(100, int(value)))
