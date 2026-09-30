from src.services.speech_assets_service import SpeechAssetsService
from src.services.speech_storage import SpeechStorage


def test_voice_catalog_has_stable_ui_metadata_and_sample_state(tmp_path):
    service = SpeechAssetsService(SpeechStorage(tmp_path))
    voices = service.list_voices()

    by_id = {voice["id"]: voice for voice in voices}
    assert {"pt_br_dora", "pt_br_alex", "pt_br_santa", "pt_br_faber", "pt_br_edresson"} <= set(by_id)

    dora = by_id["pt_br_dora"]
    assert dora["display_name"] == "Dora"
    assert dora["engine"] == "kokoro"
    assert dora["locale"] == "pt-BR"
    assert dora["source_type"] == "builtin"
    assert dora["sample_state"] == "missing"
    assert "available" in dora
    assert "unavailable_reason" in dora


def test_voice_catalog_can_apply_persisted_worker_availability(tmp_path):
    service = SpeechAssetsService(SpeechStorage(tmp_path))
    voices = service.list_voices(
        capabilities={
            "tts_engines": [
                {"id": "kokoro", "available": True, "reason": None},
                {"id": "piper", "available": False, "reason": "modelo ausente"},
            ]
        }
    )
    by_id = {voice["id"]: voice for voice in voices}
    assert by_id["pt_br_dora"]["available"] is True
    assert by_id["pt_br_faber"]["available"] is False
    assert by_id["pt_br_faber"]["unavailable_reason"] == "modelo ausente"
