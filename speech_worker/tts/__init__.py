"""Local text-to-speech engines used only by the speech worker."""

from speech_worker.tts.base import TTSDependencyError, TTSEngine, TTSEngineError, TTSEngineUnavailableError
from speech_worker.tts.registry import TTSRegistry

__all__ = [
    "TTSEngine",
    "TTSEngineError",
    "TTSDependencyError",
    "TTSEngineUnavailableError",
    "TTSRegistry",
]
