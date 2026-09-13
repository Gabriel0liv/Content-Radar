import pytest
from pydantic import ValidationError

from src.schemas.speech import SpeechSttOptions
from src.services.speech_presets import list_builtin_stt_presets, resolve_stt_config


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
