from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.speech import SpeechPreset


SpeechOperation = Literal["stt", "tts"]


class SpeechPresetError(ValueError):
    pass


class DuplicateSpeechPresetError(SpeechPresetError):
    pass


class BuiltinSpeechPresetError(SpeechPresetError):
    pass


class InvalidSpeechPresetError(SpeechPresetError):
    pass


_BUILTIN_STT: dict[str, dict[str, Any]] = {
    "fast": {
        "model": "small",
        "device": "auto",
        "compute_type": "int8",
        "batch_size": 2,
        "vad_onset": 0.5,
        "vad_offset": 0.363,
        "chunk_size": 30,
    },
    "balanced": {
        "model": "medium",
        "device": "auto",
        "compute_type": "int8",
        "batch_size": 2,
        "vad_onset": 0.5,
        "vad_offset": 0.363,
        "chunk_size": 30,
    },
    "maximum_quality": {
        "model": "large-v3",
        "device": "auto",
        "compute_type": "int8",
        "batch_size": 1,
        "vad_onset": 0.5,
        "vad_offset": 0.363,
        "chunk_size": 30,
    },
}

_BUILTIN_LABELS = {
    "fast": ("Rápido", "Prioriza velocidade com um modelo leve."),
    "balanced": ("Equilibrado", "Configuração recomendada para uso geral."),
    "maximum_quality": ("Máxima qualidade", "Prioriza fidelidade com uso conservador de memória."),
}

_STT_ALLOWED = {
    "model", "language", "device", "compute_type", "batch_size", "diarization",
    "identify_speakers", "no_diarization", "num_speakers", "min_speakers", "max_speakers",
    "quiet_speech", "vad_onset", "vad_offset", "chunk_size", "initial_prompt",
    "offline", "formats", "export_formats", "diarize_model", "cache_dir",
}
_TTS_ALLOWED = {
    "engine", "voice", "output_format", "format", "speed", "language",
    "normalize_ptbr", "analyze_ptbr", "preview", "preview_chars",
}


class SpeechPresetsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _validate_operation(operation: str) -> SpeechOperation:
        if operation not in {"stt", "tts"}:
            raise InvalidSpeechPresetError("operation deve ser 'stt' ou 'tts'")
        return operation  # type: ignore[return-value]

    @staticmethod
    def _validate_config(operation: SpeechOperation, config: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(config, dict):
            raise InvalidSpeechPresetError("config deve ser um objeto")
        allowed = _STT_ALLOWED if operation == "stt" else _TTS_ALLOWED
        unknown = set(config) - allowed
        if unknown:
            raise InvalidSpeechPresetError(f"config contém campos não suportados: {', '.join(sorted(unknown))}")
        clean = deepcopy(config)
        if operation == "stt":
            if "batch_size" in clean and (not isinstance(clean["batch_size"], int) or clean["batch_size"] < 1):
                raise InvalidSpeechPresetError("batch_size deve ser >= 1")
            if clean.get("device") not in {None, "auto", "cuda", "cpu"}:
                raise InvalidSpeechPresetError("device inválido")
            if clean.get("compute_type") not in {None, "int8", "float16", "float32"}:
                raise InvalidSpeechPresetError("compute_type inválido")
            minimum = clean.get("min_speakers")
            maximum = clean.get("max_speakers")
            if minimum is not None and maximum is not None and minimum > maximum:
                raise InvalidSpeechPresetError("min_speakers não pode exceder max_speakers")
        else:
            if clean.get("engine") not in {None, "kokoro", "piper"}:
                raise InvalidSpeechPresetError("engine TTS inválido")
            if "voice" in clean and (not isinstance(clean["voice"], str) or not clean["voice"].strip()):
                raise InvalidSpeechPresetError("voice inválida")
            speed = clean.get("speed")
            if speed is not None and (not isinstance(speed, (int, float)) or speed <= 0 or speed > 3):
                raise InvalidSpeechPresetError("speed deve estar entre 0 e 3")
            output_format = clean.get("output_format", clean.get("format"))
            if output_format not in {None, "wav", "mp3"}:
                raise InvalidSpeechPresetError("formato TTS inválido")
        return clean

    def _personal_presets(self, operation: SpeechOperation | None = None) -> list[SpeechPreset]:
        stmt = select(SpeechPreset).order_by(SpeechPreset.operation, SpeechPreset.name, SpeechPreset.id)
        if operation is not None:
            stmt = stmt.where(SpeechPreset.operation == operation)
        rows = list(self.db.execute(stmt).scalars())
        # Keep deterministic behavior for lightweight fake sessions used in unit tests.
        if operation is not None:
            rows = [item for item in rows if item.operation == operation]
        return rows

    def list_presets(self, operation: str) -> list[dict[str, Any]]:
        op = self._validate_operation(operation)
        result: list[dict[str, Any]] = []
        if op == "stt":
            for name, config in _BUILTIN_STT.items():
                label, description = _BUILTIN_LABELS[name]
                result.append({
                    "id": None,
                    "name": name,
                    "label": label,
                    "description": description,
                    "operation": "stt",
                    "config": deepcopy(config),
                    "is_builtin": True,
                })
        for preset in self._personal_presets(op):
            result.append({
                "id": preset.id,
                "name": preset.name,
                "label": preset.name,
                "description": preset.description,
                "operation": preset.operation,
                "config": deepcopy(preset.config_json or {}),
                "is_builtin": bool(preset.is_builtin),
            })
        return result

    def _ensure_unique(self, operation: SpeechOperation, name: str, *, excluding_id: int | None = None) -> None:
        normalized = name.strip().casefold()
        builtin_names = {key.casefold() for key in (_BUILTIN_STT if operation == "stt" else {})}
        if normalized in builtin_names:
            raise DuplicateSpeechPresetError("nome reservado por preset nativo")
        for preset in self._personal_presets(operation):
            if excluding_id is not None and preset.id == excluding_id:
                continue
            if preset.name.strip().casefold() == normalized:
                raise DuplicateSpeechPresetError("já existe preset com este nome para a operação")

    def create_preset(
        self,
        name: str,
        operation: str,
        config: dict[str, Any],
        description: str | None = None,
    ) -> SpeechPreset:
        op = self._validate_operation(operation)
        name = name.strip()
        if not name:
            raise InvalidSpeechPresetError("nome do preset é obrigatório")
        self._ensure_unique(op, name)
        clean = self._validate_config(op, config)
        preset = SpeechPreset(
            name=name,
            operation=op,
            description=description,
            config_json=clean,
            is_builtin=False,
        )
        self.db.add(preset)
        self.db.commit()
        self.db.refresh(preset)
        return preset

    def update_preset(
        self,
        preset_id: int,
        *,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        description: str | None = None,
    ) -> SpeechPreset:
        preset = self.db.get(SpeechPreset, preset_id)
        if preset is None:
            raise SpeechPresetError("preset não encontrado")
        if preset.is_builtin:
            raise BuiltinSpeechPresetError("preset nativo é imutável")
        op = self._validate_operation(preset.operation)
        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise InvalidSpeechPresetError("nome do preset é obrigatório")
            self._ensure_unique(op, clean_name, excluding_id=preset.id)
            preset.name = clean_name
        if config is not None:
            preset.config_json = self._validate_config(op, config)
        if description is not None:
            preset.description = description
        self.db.commit()
        self.db.refresh(preset)
        return preset

    def delete_preset(self, preset_id: int) -> bool:
        preset = self.db.get(SpeechPreset, preset_id)
        if preset is None:
            return False
        if preset.is_builtin:
            raise BuiltinSpeechPresetError("preset nativo é imutável")
        self.db.delete(preset)
        self.db.commit()
        return True

    def update_builtin(self, operation: str, name: str, config: dict[str, Any]) -> None:
        raise BuiltinSpeechPresetError("presets nativos são imutáveis")

    def delete_builtin(self, operation: str, name: str) -> None:
        raise BuiltinSpeechPresetError("presets nativos são imutáveis")

    def resolve_stt_preset(self, name: str) -> dict[str, Any]:
        canonical = "maximum_quality" if name == "max_quality" else name
        if canonical in _BUILTIN_STT:
            return deepcopy(_BUILTIN_STT[canonical])
        return self._resolve_personal("stt", name)

    def resolve_tts_preset(self, name: str) -> dict[str, Any]:
        return self._resolve_personal("tts", name)

    def _resolve_personal(self, operation: SpeechOperation, name: str) -> dict[str, Any]:
        normalized = name.strip().casefold()
        for preset in self._personal_presets(operation):
            if preset.name.strip().casefold() == normalized:
                return deepcopy(preset.config_json or {})
        raise SpeechPresetError("preset não encontrado")
