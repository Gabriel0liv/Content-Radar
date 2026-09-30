from pathlib import Path

import pytest

from src.services.speech_assets_service import SpeechAssetsService
from src.services.speech_storage import SpeechStorage


def test_voice_sample_path_is_managed_and_becomes_ready(tmp_path):
    storage = SpeechStorage(tmp_path)
    service = SpeechAssetsService(storage)

    descriptor = service.get_sample("pt_br_dora")
    assert descriptor["state"] == "missing"
    assert descriptor["storage_key"] is None

    path = service.sample_path("pt_br_dora")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFFsample")

    descriptor = service.get_sample("pt_br_dora")
    assert descriptor["state"] == "ready"
    assert descriptor["storage_key"] == "assets/voice_samples/pt_br_dora.wav"
    assert (storage.root / descriptor["storage_key"]).resolve() == path.resolve()


def test_unknown_or_path_escape_voice_id_is_rejected(tmp_path):
    service = SpeechAssetsService(SpeechStorage(tmp_path))
    with pytest.raises(ValueError):
        service.sample_path("../../secret")
    with pytest.raises(ValueError):
        service.sample_path("not-a-real-voice")
