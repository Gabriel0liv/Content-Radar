from __future__ import annotations

import importlib.util
import io
import os
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from speech_worker.tts.base import TTSDependencyError, TTSEngine, TTSEngineError
from speech_worker.tts.kokoro_engine import setup_espeak


_PIPER_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
_PIPER_MODELS = {
    "pt_BR-faber-medium": "pt/pt_BR/faber/medium/pt_BR-faber-medium",
    "pt_BR-edresson-low": "pt/pt_BR/edresson/low/pt_BR-edresson-low",
}


class PiperEngine(TTSEngine):
    name = "piper"

    def __init__(self, voice_id: str, *, device: str = "cpu", cache_dir: str | Path | None = None, **options: Any) -> None:
        super().__init__(voice_id, device=device, cache_dir=cache_dir, **options)
        self._voice: Any = None
        self._model_path: Path | None = None

    @classmethod
    def availability(cls) -> dict[str, Any]:
        missing = [name for name in ("piper", "onnxruntime") if importlib.util.find_spec(name) is None]
        if missing:
            return {"available": False, "reason": f"dependências ausentes: {', '.join(missing)}"}
        if not setup_espeak():
            return {"available": False, "reason": "eSpeak NG não encontrado"}
        return {"available": True, "reason": None}

    def _voice_root(self) -> Path:
        root = self.cache_dir or Path(os.getenv("SPEECH_VOICES_DIR", "data/speech/voices"))
        root = Path(root).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _resolve_model(self) -> Path:
        candidate = Path(self.voice_id)
        if candidate.suffix.lower() == ".onnx" or candidate.is_absolute():
            model = candidate.expanduser().resolve()
        else:
            model = self._voice_root() / f"{self.voice_id}.onnx"
        config = Path(str(model) + ".json")
        if model.exists() and config.exists():
            return model

        if bool(self.options.get("offline")):
            raise TTSDependencyError(self.name, f"modelo de voz não disponível offline: {model.name}")
        model_id = model.stem
        relative = _PIPER_MODELS.get(model_id)
        if relative is None:
            raise TTSDependencyError(self.name, f"modelo de voz não encontrado: {model_id}")

        for suffix in ("", ".json"):
            destination = Path(str(model) + suffix)
            url = f"{_PIPER_BASE_URL}/{relative}.onnx{suffix}?download=true"
            try:
                urllib.request.urlretrieve(url, destination)
            except (urllib.error.URLError, OSError) as exc:
                destination.unlink(missing_ok=True)
                raise TTSDependencyError(self.name, f"falha ao obter modelo de voz {model_id}") from exc
        return model

    def _load_voice(self) -> Any:
        status = self.availability()
        if not status["available"]:
            raise TTSDependencyError(self.name, str(status["reason"]))
        if self._voice is not None:
            return self._voice
        try:
            from piper import PiperVoice  # type: ignore
        except ImportError as exc:
            raise TTSDependencyError(self.name, "pacote piper-tts não instalado") from exc

        self._model_path = self._resolve_model()
        config = Path(str(self._model_path) + ".json")
        try:
            self._voice = PiperVoice.load(
                str(self._model_path),
                config_path=str(config),
                use_cuda=self.device.lower() == "cuda",
            )
        except Exception as exc:
            raise TTSEngineError(f"piper: falha ao carregar voz ({type(exc).__name__})") from exc
        return self._voice

    def synthesize_to_array(self, text: str) -> tuple[Any, int]:
        if not text or not text.strip():
            raise TTSEngineError("piper: texto vazio")
        voice = self._load_voice()
        sample_rate = int(getattr(getattr(voice, "config", None), "sample_rate", 22050))
        buffer = io.BytesIO()
        try:
            with wave.open(buffer, "wb") as wav_file:
                voice.synthesize_wav(text, wav_file)
        except AttributeError:
            try:
                chunks = list(voice.synthesize(text))
                raw = b"".join(
                    chunk.audio_int16 if hasattr(chunk, "audio_int16") else bytes(chunk)
                    for chunk in chunks
                )
                if not raw:
                    raise TTSEngineError("piper: nenhum áudio gerado")
                buffer = io.BytesIO()
                with wave.open(buffer, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(raw)
            except TTSEngineError:
                raise
            except Exception as exc:
                raise TTSEngineError(f"piper: falha durante síntese ({type(exc).__name__})") from exc
        except Exception as exc:
            raise TTSEngineError(f"piper: falha durante síntese ({type(exc).__name__})") from exc

        buffer.seek(0)
        with wave.open(buffer, "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            raw = wav_file.readframes(wav_file.getnframes())
        try:
            import numpy as np
        except ImportError as exc:
            raise TTSDependencyError(self.name, "numpy não instalado") from exc
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio, sample_rate
