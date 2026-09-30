from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from src.services.speech_storage import SpeechStorage
from speech_worker.tts.registry import canonical_voice_descriptors


class SpeechAssetsService:
    def __init__(self, storage: SpeechStorage) -> None:
        self.storage = storage
        self._voices = {voice["id"]: voice for voice in canonical_voice_descriptors()}

    def _voice(self, voice_id: str) -> dict[str, Any]:
        voice = self._voices.get(voice_id)
        if voice is None:
            raise ValueError("Voz TTS desconhecida")
        return voice

    def get_voice(self, voice_id: str) -> dict[str, Any]:
        return deepcopy(self._voice(voice_id))

    def voice_samples_dir(self) -> Path:
        path = self.storage.root / "assets" / "voice_samples"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def sample_path(self, voice_id: str) -> Path:
        self._voice(voice_id)
        path = (self.voice_samples_dir() / f"{voice_id}.wav").resolve()
        try:
            path.relative_to(self.voice_samples_dir().resolve())
        except ValueError as exc:
            raise ValueError("Caminho de amostra fora do armazenamento gerenciado") from exc
        return path

    def get_sample(self, voice_id: str) -> dict[str, Any]:
        self._voice(voice_id)
        path = self.sample_path(voice_id)
        ready = path.is_file()
        return {
            "voice_id": voice_id,
            "state": "ready" if ready else "missing",
            "storage_key": self.storage.safe_storage_key(path) if ready else None,
            "mime_type": "audio/wav" if ready else None,
            "size_bytes": path.stat().st_size if ready else None,
        }

    @staticmethod
    def _engine_availability(capabilities: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        if not capabilities:
            return result
        engines = capabilities.get("tts_engines") or []
        for item in engines:
            if isinstance(item, str):
                result[item] = {"available": True, "reason": None}
            elif isinstance(item, dict) and item.get("id"):
                result[str(item["id"])] = {
                    "available": bool(item.get("available")),
                    "reason": item.get("reason"),
                }
        return result

    def list_voices(self, *, capabilities: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        engine_availability = self._engine_availability(capabilities)
        voices: list[dict[str, Any]] = []
        for descriptor in self._voices.values():
            item = deepcopy(descriptor)
            engine_state = engine_availability.get(item["engine"])
            if engine_state is None:
                item["available"] = False
                item["unavailable_reason"] = "worker não informou disponibilidade do motor"
            else:
                item["available"] = bool(engine_state["available"])
                item["unavailable_reason"] = None if item["available"] else engine_state.get("reason")
            sample = self.get_sample(item["id"])
            item["sample_state"] = sample["state"]
            item["sample_storage_key"] = sample["storage_key"]
            voices.append(item)
        return voices
