from __future__ import annotations

import importlib.util
import os
import shutil
from pathlib import Path
from typing import Any

from speech_worker.tts.base import TTSDependencyError, TTSEngine, TTSEngineError


def setup_espeak() -> bool:
    configured = os.getenv("PHONEMIZER_ESPEAK_PATH")
    if configured and Path(configured).exists():
        return True
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        return True
    for candidate in (
        Path(r"C:\Program Files\eSpeak NG"),
        Path(r"C:\Program Files (x86)\eSpeak NG"),
        Path(r"C:\Program Files\eSpeak"),
        Path(r"C:\Program Files (x86)\eSpeak"),
    ):
        if (candidate / "espeak-ng.exe").exists() or (candidate / "espeak.exe").exists():
            os.environ["PHONEMIZER_ESPEAK_PATH"] = str(candidate)
            os.environ["PATH"] = str(candidate) + os.pathsep + os.environ.get("PATH", "")
            return True
    return False


def get_lang_code_for_voice(voice: str) -> str:
    value = voice.lower()
    if value.startswith(("pf_", "pm_")):
        return "p"
    if value.startswith(("bf_", "bm_")):
        return "b"
    if value.startswith(("ef_", "em_")):
        return "e"
    if value.startswith(("ff_", "fm_")):
        return "f"
    if value.startswith(("hf_", "hm_")):
        return "h"
    if value.startswith(("if_", "im_")):
        return "i"
    if value.startswith(("jf_", "jm_")):
        return "j"
    if value.startswith(("zf_", "zm_")):
        return "z"
    return "a"


class KokoroEngine(TTSEngine):
    name = "kokoro"

    def __init__(self, voice_id: str, *, device: str = "cpu", cache_dir: str | Path | None = None, **options: Any) -> None:
        super().__init__(voice_id, device=device, cache_dir=cache_dir, **options)
        self._pipeline: Any = None
        self._lang_code: str | None = None

    @classmethod
    def availability(cls) -> dict[str, Any]:
        missing = [name for name in ("kokoro", "torch", "soundfile") if importlib.util.find_spec(name) is None]
        if missing:
            return {"available": False, "reason": f"dependências ausentes: {', '.join(missing)}"}
        if not setup_espeak():
            return {"available": False, "reason": "eSpeak NG não encontrado"}
        return {"available": True, "reason": None}

    def _get_pipeline(self) -> Any:
        status = self.availability()
        if not status["available"]:
            raise TTSDependencyError(self.name, str(status["reason"]))
        lang_code = get_lang_code_for_voice(self.voice_id)
        if self._pipeline is not None and self._lang_code == lang_code:
            return self._pipeline

        try:
            from kokoro import KPipeline  # type: ignore
        except ImportError as exc:
            raise TTSDependencyError(self.name, "pacote kokoro não instalado") from exc

        kwargs: dict[str, Any] = {
            "lang_code": lang_code,
            "device": self.device,
            "repo_id": "hexgrad/Kokoro-82M",
        }
        if self.cache_dir:
            os.environ.setdefault("HF_HOME", str(self.cache_dir))
        try:
            self._pipeline = KPipeline(**kwargs)
        except Exception as exc:
            raise TTSEngineError(f"kokoro: falha ao carregar pipeline ({type(exc).__name__})") from exc
        self._lang_code = lang_code
        return self._pipeline

    def synthesize_to_array(self, text: str) -> tuple[Any, int]:
        if not text or not text.strip():
            raise TTSEngineError("kokoro: texto vazio")
        pipeline = self._get_pipeline()
        speed = float(self.options.get("speed", 1.0))
        try:
            import numpy as np
            chunks = [audio for _, _, audio in pipeline(text, voice=self.voice_id, speed=speed) if audio is not None and len(audio)]
            if not chunks:
                raise TTSEngineError("kokoro: nenhum áudio gerado")
            return np.concatenate(chunks), 24000
        except TTSEngineError:
            raise
        except Exception as exc:
            raise TTSEngineError(f"kokoro: falha durante síntese ({type(exc).__name__})") from exc
