from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


class InvalidSpeechSettingsError(ValueError):
    pass


_DEFAULTS: dict[str, Any] = {
    "default_stt_preset": "balanced",
    "default_language": None,
    "default_diarization": False,
    "default_tts_engine": "kokoro",
    "default_voice": None,
    "default_output_format": "wav",
    "default_ptbr_normalization": False,
    "default_export_formats": ["txt", "json", "srt", "vtt"],
    "offline_mode": False,
    "artifact_retention_days": 90,
    "input_retention_days": 7,
    "retain_debug_artifacts": False,
    "hardware_policy": "auto",
}

_ALLOWED_KEYS = set(_DEFAULTS)


class SpeechSettingsService:
    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("SPEECH_SETTINGS_PATH") or "data/speech/settings.json"
        self.path = Path(configured)

    def _read_persisted(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidSpeechSettingsError("arquivo de configurações de áudio inválido") from exc
        if not isinstance(raw, dict):
            raise InvalidSpeechSettingsError("configurações persistidas devem ser um objeto")
        unknown = set(raw) - _ALLOWED_KEYS
        if unknown:
            raise InvalidSpeechSettingsError("arquivo contém configurações não suportadas")
        return self._validate(raw, partial=True)

    @staticmethod
    def _validate(values: dict[str, Any], *, partial: bool) -> dict[str, Any]:
        if not isinstance(values, dict):
            raise InvalidSpeechSettingsError("configurações devem ser um objeto")
        unknown = set(values) - _ALLOWED_KEYS
        if unknown:
            raise InvalidSpeechSettingsError(f"configuração não suportada: {', '.join(sorted(unknown))}")
        result = deepcopy(values)

        if "default_stt_preset" in result and result["default_stt_preset"] not in {"fast", "balanced", "maximum_quality", "max_quality"}:
            raise InvalidSpeechSettingsError("default_stt_preset inválido")
        if "default_language" in result and result["default_language"] is not None:
            if not isinstance(result["default_language"], str) or not result["default_language"].strip():
                raise InvalidSpeechSettingsError("default_language inválido")
        if "default_diarization" in result and not isinstance(result["default_diarization"], bool):
            raise InvalidSpeechSettingsError("default_diarization deve ser booleano")
        if "default_tts_engine" in result and result["default_tts_engine"] not in {"kokoro", "piper"}:
            raise InvalidSpeechSettingsError("default_tts_engine inválido")
        if "default_voice" in result and result["default_voice"] is not None:
            if not isinstance(result["default_voice"], str) or not result["default_voice"].strip():
                raise InvalidSpeechSettingsError("default_voice inválida")
        if "default_output_format" in result and result["default_output_format"] not in {"wav", "mp3"}:
            raise InvalidSpeechSettingsError("default_output_format inválido")
        if "default_ptbr_normalization" in result and not isinstance(result["default_ptbr_normalization"], bool):
            raise InvalidSpeechSettingsError("default_ptbr_normalization deve ser booleano")
        if "default_export_formats" in result:
            formats = result["default_export_formats"]
            if not isinstance(formats, list) or not formats or any(item not in {"txt", "json", "srt", "vtt"} for item in formats):
                raise InvalidSpeechSettingsError("default_export_formats inválido")
            result["default_export_formats"] = list(dict.fromkeys(formats))
        if "offline_mode" in result and not isinstance(result["offline_mode"], bool):
            raise InvalidSpeechSettingsError("offline_mode deve ser booleano")
        for key in ("artifact_retention_days", "input_retention_days"):
            if key in result and (not isinstance(result[key], int) or result[key] < 0 or result[key] > 3650):
                raise InvalidSpeechSettingsError(f"{key} deve estar entre 0 e 3650")
        if "retain_debug_artifacts" in result and not isinstance(result["retain_debug_artifacts"], bool):
            raise InvalidSpeechSettingsError("retain_debug_artifacts deve ser booleano")
        if "hardware_policy" in result and result["hardware_policy"] not in {"auto", "cuda", "cpu"}:
            raise InvalidSpeechSettingsError("hardware_policy inválido")
        return result

    def get_speech_settings(self) -> dict[str, Any]:
        settings = deepcopy(_DEFAULTS)
        settings.update(self._read_persisted())
        settings["hf_token_configured"] = bool(os.getenv("HF_TOKEN"))
        return settings

    def update_speech_settings(self, changes: dict[str, Any]) -> dict[str, Any]:
        clean = self._validate(changes, partial=True)
        current = self._read_persisted()
        candidate = deepcopy(_DEFAULTS)
        candidate.update(current)
        candidate.update(clean)
        persisted = {key: deepcopy(candidate[key]) for key in _DEFAULTS}
        self._validate(persisted, partial=False)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        try:
            temp.write_text(json.dumps(persisted, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(self.path)
        except OSError:
            temp.unlink(missing_ok=True)
            raise
        return self.get_speech_settings()


def get_speech_settings(path: str | Path | None = None) -> dict[str, Any]:
    return SpeechSettingsService(path).get_speech_settings()


def update_speech_settings(changes: dict[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    return SpeechSettingsService(path).update_speech_settings(changes)
