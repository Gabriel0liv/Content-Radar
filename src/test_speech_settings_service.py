import json
from pathlib import Path

import pytest

from src.services.speech_settings_service import InvalidSpeechSettingsError, SpeechSettingsService


def test_defaults_are_returned_when_settings_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    service = SpeechSettingsService(tmp_path / "settings.json")
    settings = service.get_speech_settings()
    assert settings["default_stt_preset"] == "balanced"
    assert settings["default_tts_engine"] == "kokoro"
    assert settings["default_output_format"] == "wav"
    assert settings["hf_token_configured"] is False


def test_update_persists_supported_defaults_atomically(tmp_path):
    path = tmp_path / "settings.json"
    service = SpeechSettingsService(path)
    updated = service.update_speech_settings({
        "default_language": "pt",
        "default_diarization": True,
        "default_tts_engine": "piper",
        "default_voice": "pt_br_faber",
        "default_output_format": "mp3",
        "default_ptbr_normalization": True,
        "default_export_formats": ["txt", "srt", "vtt"],
        "offline_mode": True,
        "artifact_retention_days": 30,
        "input_retention_days": 7,
        "retain_debug_artifacts": False,
        "hardware_policy": "auto",
    })
    assert updated["default_tts_engine"] == "piper"
    assert json.loads(path.read_text(encoding="utf-8"))["artifact_retention_days"] == 30
    assert not (tmp_path / "settings.json.tmp").exists()


def test_hf_secret_is_presence_only_and_never_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_super-secret")
    path = tmp_path / "settings.json"
    service = SpeechSettingsService(path)
    result = service.update_speech_settings({"default_language": "pt-br"})
    assert result["hf_token_configured"] is True
    assert "hf_super-secret" not in json.dumps(result)
    assert "hf_super-secret" not in path.read_text(encoding="utf-8")
    assert "hf_token" not in json.loads(path.read_text(encoding="utf-8"))


def test_unknown_or_secret_setting_keys_are_rejected(tmp_path):
    service = SpeechSettingsService(tmp_path / "settings.json")
    with pytest.raises(InvalidSpeechSettingsError):
        service.update_speech_settings({"hf_token": "secret"})
    with pytest.raises(InvalidSpeechSettingsError):
        service.update_speech_settings({"mystery_setting": True})


def test_invalid_settings_values_do_not_overwrite_previous_file(tmp_path):
    path = tmp_path / "settings.json"
    service = SpeechSettingsService(path)
    service.update_speech_settings({"default_tts_engine": "piper"})
    before = path.read_text(encoding="utf-8")
    with pytest.raises(InvalidSpeechSettingsError):
        service.update_speech_settings({"default_tts_engine": "invalid"})
    assert path.read_text(encoding="utf-8") == before


def test_corrupt_settings_file_fails_explicitly_instead_of_silently_resetting(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{not-json", encoding="utf-8")
    service = SpeechSettingsService(path)
    with pytest.raises(InvalidSpeechSettingsError):
        service.get_speech_settings()
