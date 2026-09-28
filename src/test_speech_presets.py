from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.models.speech import SpeechPreset
from src.schemas.speech import SpeechSttOptions
from src.services.speech_presets import list_builtin_stt_presets, resolve_stt_config
from src.services.speech_presets_service import (
    BuiltinSpeechPresetError,
    DuplicateSpeechPresetError,
    InvalidSpeechPresetError,
    SpeechPresetsService,
)


class ScalarResult:
    def __init__(self, items=None):
        self.items = items or []

    def scalars(self):
        return iter(self.items)

    def scalar_one_or_none(self):
        return self.items[0] if self.items else None


class FakePresetSession:
    def __init__(self):
        self.items = {}
        self.next_id = 1
        self.commits = 0
        self.last_stmt = None

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = self.next_id
            self.next_id += 1
        self.items[obj.id] = obj

    def get(self, model, key):
        return self.items.get(key)

    def delete(self, obj):
        self.items.pop(obj.id, None)

    def commit(self):
        self.commits += 1

    def refresh(self, obj):
        return None

    def execute(self, stmt):
        self.last_stmt = stmt
        # The service keeps filtering deterministic; for the fake, return all
        # persisted personal presets and let service-side guards remain testable.
        return ScalarResult(list(self.items.values()))


def test_fast_preset_is_lightweight():
    result = resolve_stt_config(SpeechSttOptions(preset="fast"))
    assert result.model == "small"
    assert result.compute_type == "int8"
    assert result.batch_size == 2
    assert result.no_diarization is True
    assert result.vad_onset == 0.500
    assert result.vad_offset == 0.363


def test_balanced_preset_is_default_general_mode():
    result = resolve_stt_config(SpeechSttOptions(preset="balanced", identify_speakers=True))
    assert result.model == "medium"
    assert result.compute_type == "int8"
    assert result.no_diarization is False
    assert result.batch_size == 2


def test_max_quality_prefers_safe_memory_settings():
    result = resolve_stt_config(SpeechSttOptions(preset="max_quality"))
    assert result.model == "large-v3"
    assert result.compute_type == "int8"
    assert result.batch_size == 1


def test_quiet_speech_enables_sensitive_vad():
    result = resolve_stt_config(SpeechSttOptions(preset="balanced", quiet_speech=True))
    assert result.vad_onset == 0.1
    assert result.vad_offset == 0.1


def test_exact_speaker_count_wins_over_range():
    result = resolve_stt_config(
        SpeechSttOptions(
            preset="balanced",
            identify_speakers=True,
            num_speakers=2,
            min_speakers=1,
            max_speakers=4,
        )
    )
    assert result.num_speakers == 2
    assert result.min_speakers is None
    assert result.max_speakers is None


def test_speaker_range_requires_valid_order():
    with pytest.raises(ValidationError):
        SpeechSttOptions(
            preset="balanced",
            identify_speakers=True,
            min_speakers=4,
            max_speakers=2,
        )


def test_builtin_presets_have_user_facing_labels():
    presets = list_builtin_stt_presets()
    assert [preset.name for preset in presets] == ["fast", "balanced", "max_quality"]
    assert [preset.label for preset in presets] == ["Rápido", "Equilibrado", "Máxima qualidade"]


def test_native_service_exposes_required_builtin_names():
    service = SpeechPresetsService(FakePresetSession())
    presets = service.list_presets("stt")
    assert [item["name"] for item in presets[:3]] == ["fast", "balanced", "maximum_quality"]
    assert all(item["is_builtin"] for item in presets[:3])


def test_personal_stt_and_tts_presets_crud_independently():
    session = FakePresetSession()
    service = SpeechPresetsService(session)
    stt = service.create_preset("Meu modo", "stt", {"model": "medium", "device": "auto"})
    tts = service.create_preset("Minha voz", "tts", {"engine": "kokoro", "voice": "pt_br_dora", "speed": 1.0})
    assert stt.operation == "stt"
    assert tts.operation == "tts"

    updated = service.update_preset(tts.id, name="Narrador", config={"engine": "piper", "voice": "pt_br_faber", "speed": 0.95})
    assert updated.name == "Narrador"
    assert updated.config_json["engine"] == "piper"

    assert service.delete_preset(stt.id) is True
    assert session.get(SpeechPreset, stt.id) is None


def test_duplicate_personal_name_is_scoped_by_operation():
    session = FakePresetSession()
    service = SpeechPresetsService(session)
    service.create_preset("Podcast", "stt", {"model": "medium"})
    with pytest.raises(DuplicateSpeechPresetError):
        service.create_preset("Podcast", "stt", {"model": "small"})
    # Same human name is valid for the other operation.
    other = service.create_preset("Podcast", "tts", {"engine": "kokoro", "voice": "pt_br_dora"})
    assert other.operation == "tts"


def test_builtin_presets_cannot_be_updated_or_deleted():
    service = SpeechPresetsService(FakePresetSession())
    with pytest.raises(BuiltinSpeechPresetError):
        service.update_builtin("stt", "balanced", {"model": "tiny"})
    with pytest.raises(BuiltinSpeechPresetError):
        service.delete_builtin("stt", "balanced")


def test_invalid_operation_specific_config_is_rejected_before_persisting():
    service = SpeechPresetsService(FakePresetSession())
    with pytest.raises(InvalidSpeechPresetError):
        service.create_preset("Quebrado", "tts", {"engine": "unknown", "voice": "x"})
    with pytest.raises(InvalidSpeechPresetError):
        service.create_preset("Quebrado STT", "stt", {"batch_size": 0})


def test_resolve_personal_preset_returns_copy_of_config():
    session = FakePresetSession()
    service = SpeechPresetsService(session)
    preset = service.create_preset("Dora", "tts", {"engine": "kokoro", "voice": "pt_br_dora", "speed": 1.0})
    resolved = service.resolve_tts_preset("Dora")
    resolved["speed"] = 2.0
    assert preset.config_json["speed"] == 1.0
