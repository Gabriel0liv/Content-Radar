from __future__ import annotations

from copy import deepcopy
from typing import Any, Type

from speech_worker.tts.base import TTSEngine, TTSEngineUnavailableError


_CANONICAL_VOICES: tuple[dict[str, Any], ...] = (
    {
        "id": "pt_br_dora",
        "engine": "kokoro",
        "engine_voice_id": "pf_dora",
        "display_name": "Dora",
        "language": "pt-br",
        "locale": "pt-BR",
        "gender": "Feminino",
        "style": "Suave / Natural",
        "source_type": "builtin",
    },
    {
        "id": "pt_br_alex",
        "engine": "kokoro",
        "engine_voice_id": "pm_alex",
        "display_name": "Alex",
        "language": "pt-br",
        "locale": "pt-BR",
        "gender": "Masculino",
        "style": "Natural",
        "source_type": "builtin",
    },
    {
        "id": "pt_br_santa",
        "engine": "kokoro",
        "engine_voice_id": "pm_santa",
        "display_name": "Santa",
        "language": "pt-br",
        "locale": "pt-BR",
        "gender": "Masculino",
        "style": "Grave / Narrativo",
        "source_type": "builtin",
    },
    {
        "id": "pt_br_faber",
        "engine": "piper",
        "engine_voice_id": "pt_BR-faber-medium",
        "display_name": "Faber",
        "language": "pt-br",
        "locale": "pt-BR",
        "gender": "Masculino",
        "style": "Narrativo",
        "source_type": "downloadable",
    },
    {
        "id": "pt_br_edresson",
        "engine": "piper",
        "engine_voice_id": "pt_BR-edresson-low",
        "display_name": "Edresson",
        "language": "pt-br",
        "locale": "pt-BR",
        "gender": "Masculino",
        "style": "Natural / Conversacional",
        "source_type": "downloadable",
    },
)

_ALIASES = {
    "dora": "pt_br_dora",
    "kokoro_dora": "pt_br_dora",
    "alex": "pt_br_alex",
    "kokoro_alex": "pt_br_alex",
    "santa": "pt_br_santa",
    "kokoro_santa": "pt_br_santa",
    "faber": "pt_br_faber",
    "piper_faber": "pt_br_faber",
    "edresson": "pt_br_edresson",
    "piper_edresson": "pt_br_edresson",
}


class TTSRegistry:
    def __init__(self, *, register_defaults: bool = True) -> None:
        self._engines: dict[str, Type[TTSEngine]] = {}
        self._voices: dict[str, dict[str, Any]] = {}
        if register_defaults:
            from speech_worker.tts.kokoro_engine import KokoroEngine
            from speech_worker.tts.piper_engine import PiperEngine

            self.register("kokoro", KokoroEngine)
            self.register("piper", PiperEngine)
            for voice in _CANONICAL_VOICES:
                self.register_voice(voice)

    def register(self, name: str, engine_cls: Type[TTSEngine]) -> None:
        self._engines[name.strip().lower()] = engine_cls

    def register_voice(self, descriptor: dict[str, Any]) -> None:
        required = {"id", "engine", "engine_voice_id", "display_name", "language", "locale", "source_type"}
        missing = required - set(descriptor)
        if missing:
            raise ValueError(f"descritor de voz incompleto: {', '.join(sorted(missing))}")
        voice_id = str(descriptor["id"]).strip()
        if not voice_id:
            raise ValueError("id da voz é obrigatório")
        self._voices[voice_id] = deepcopy(descriptor)

    def get_engine_class(self, name: str) -> Type[TTSEngine]:
        normalized = name.strip().lower()
        engine_cls = self._engines.get(normalized)
        if engine_cls is None:
            raise TTSEngineUnavailableError(f"motor TTS '{name}' não registrado")
        return engine_cls

    def resolve_voice(self, engine: str, voice_id: str) -> str:
        canonical = _ALIASES.get(voice_id, voice_id)
        descriptor = self._voices.get(canonical)
        if descriptor is None:
            return voice_id
        if descriptor["engine"] != engine.lower():
            raise TTSEngineUnavailableError(
                f"voz '{voice_id}' pertence ao motor {descriptor['engine']}, não {engine}"
            )
        return str(descriptor["engine_voice_id"])

    def create_engine(
        self,
        name: str,
        voice_id: str,
        *,
        device: str = "cpu",
        cache_dir: str | None = None,
        **options: Any,
    ) -> TTSEngine:
        engine_cls = self.get_engine_class(name)
        availability = engine_cls.availability()
        if not availability.get("available"):
            reason = availability.get("reason") or "motor indisponível"
            raise TTSEngineUnavailableError(f"{name}: {reason}")
        resolved_voice = self.resolve_voice(name.lower(), voice_id)
        return engine_cls(
            resolved_voice,
            device=device,
            cache_dir=cache_dir,
            **options,
        )

    def list_engines(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for name, engine_cls in self._engines.items():
            availability = engine_cls.availability()
            result.append(
                {
                    "id": name,
                    "available": bool(availability.get("available")),
                    "reason": availability.get("reason"),
                }
            )
        return result

    def list_voices(self, *, engine: str | None = None, language: str | None = None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for descriptor in self._voices.values():
            if engine is not None and descriptor["engine"] != engine.lower():
                continue
            if language is not None and descriptor["language"].lower() != language.lower():
                continue
            item = deepcopy(descriptor)
            engine_cls = self._engines.get(item["engine"])
            availability = engine_cls.availability() if engine_cls else {"available": False, "reason": "motor não registrado"}
            item["available"] = bool(availability.get("available"))
            item["unavailable_reason"] = None if item["available"] else availability.get("reason")
            result.append(item)
        return result
