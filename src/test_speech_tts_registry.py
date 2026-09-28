import pytest

from speech_worker.tts.base import TTSEngine, TTSDependencyError, TTSEngineUnavailableError
from speech_worker.tts.registry import TTSRegistry


class ReadyEngine(TTSEngine):
    @classmethod
    def availability(cls):
        return {"available": True, "reason": None}

    def synthesize_to_array(self, text: str):
        return [0.0], 24000


class MissingEngine(TTSEngine):
    @classmethod
    def availability(cls):
        return {"available": False, "reason": "runtime ausente"}

    def synthesize_to_array(self, text: str):
        raise AssertionError("não deve sintetizar")


def test_registry_resolves_engine_and_voice_alias_without_loading_model():
    registry = TTSRegistry(register_defaults=False)
    registry.register("ready", ReadyEngine)
    registry.register_voice({
        "id": "pt_br_test",
        "engine": "ready",
        "engine_voice_id": "internal_voice",
        "display_name": "Teste",
        "language": "pt-br",
        "locale": "pt-BR",
        "style": "Natural",
        "source_type": "builtin",
    })
    engine = registry.create_engine("ready", "pt_br_test", speed=1.1)
    assert isinstance(engine, ReadyEngine)
    assert engine.voice_id == "internal_voice"
    assert engine.options["speed"] == 1.1


def test_registry_rejects_unknown_engine_with_normalized_error():
    registry = TTSRegistry(register_defaults=False)
    with pytest.raises(TTSEngineUnavailableError, match="não registrado"):
        registry.create_engine("missing", "voice")


def test_registry_reports_unavailable_engine_without_raw_import_error():
    registry = TTSRegistry(register_defaults=False)
    registry.register("missing", MissingEngine)
    with pytest.raises(TTSEngineUnavailableError, match="runtime ausente"):
        registry.create_engine("missing", "voice")


def test_registry_lists_canonical_ptbr_voices_once():
    registry = TTSRegistry()
    voices = registry.list_voices(language="pt-br")
    ids = [voice["id"] for voice in voices]
    assert ids == [
        "pt_br_dora",
        "pt_br_alex",
        "pt_br_santa",
        "pt_br_faber",
        "pt_br_edresson",
    ]
    assert all(voice["language"] == "pt-br" for voice in voices)
    assert {voice["engine"] for voice in voices} == {"kokoro", "piper"}


def test_voice_descriptor_contains_stable_metadata_and_availability():
    registry = TTSRegistry(register_defaults=False)
    registry.register("ready", ReadyEngine)
    registry.register_voice({
        "id": "voice_1",
        "engine": "ready",
        "engine_voice_id": "inner",
        "display_name": "Voice One",
        "language": "pt-br",
        "locale": "pt-BR",
        "style": "Narrativa",
        "source_type": "local",
    })
    voice = registry.list_voices()[0]
    assert voice["id"] == "voice_1"
    assert voice["display_name"] == "Voice One"
    assert voice["engine"] == "ready"
    assert voice["locale"] == "pt-BR"
    assert voice["source_type"] == "local"
    assert voice["available"] is True
    assert voice["unavailable_reason"] is None


def test_dependency_error_is_safe_and_does_not_expose_original_exception_repr():
    error = TTSDependencyError("kokoro", "eSpeak NG não encontrado")
    assert str(error) == "kokoro: eSpeak NG não encontrado"
