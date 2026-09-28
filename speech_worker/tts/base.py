from __future__ import annotations

import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class TTSEngineError(RuntimeError):
    """Base error safe to persist as a normalized speech job failure."""


class TTSDependencyError(TTSEngineError):
    def __init__(self, engine: str, reason: str) -> None:
        self.engine = engine
        self.reason = reason
        super().__init__(f"{engine}: {reason}")


class TTSEngineUnavailableError(TTSEngineError):
    pass


class TTSEngine(ABC):
    name = "tts"

    def __init__(
        self,
        voice_id: str,
        *,
        device: str = "cpu",
        cache_dir: str | Path | None = None,
        **options: Any,
    ) -> None:
        self.voice_id = voice_id
        self.device = device
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self.options = dict(options)

    @classmethod
    @abstractmethod
    def availability(cls) -> dict[str, Any]:
        """Return a side-effect-free availability probe."""

    @classmethod
    def is_available(cls) -> bool:
        return bool(cls.availability().get("available"))

    @abstractmethod
    def synthesize_to_array(self, text: str) -> tuple[Any, int]:
        """Return mono floating point audio and sample rate."""

    def synthesize(self, text: str, output_path: str | Path, output_format: str = "wav") -> Path:
        if not text or not text.strip():
            raise TTSEngineError("texto TTS vazio")
        output_format = output_format.lower()
        if output_format not in {"wav", "mp3"}:
            raise TTSEngineError("formato TTS não suportado; use wav ou mp3")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        audio, sample_rate = self.synthesize_to_array(text)

        try:
            import soundfile as sf  # type: ignore
        except ImportError as exc:
            raise TTSDependencyError(self.name, "pacote soundfile não instalado") from exc

        if output_format == "wav":
            sf.write(str(output), audio, sample_rate)
            return output.resolve()

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise TTSDependencyError(self.name, "FFmpeg não encontrado para exportar MP3")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=str(output.parent)) as handle:
            temp_wav = Path(handle.name)
        try:
            sf.write(str(temp_wav), audio, sample_rate)
            process = subprocess.run(
                [ffmpeg, "-y", "-loglevel", "error", "-i", str(temp_wav), str(output)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if process.returncode != 0 or not output.exists():
                raise TTSDependencyError(self.name, "FFmpeg falhou ao exportar MP3")
        finally:
            temp_wav.unlink(missing_ok=True)
        return output.resolve()
