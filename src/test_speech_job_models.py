from sqlalchemy import inspect

from src.models.speech import SpeechArtifact, SpeechJob, SpeechPreset, SpeechSpeakerMapping, SpeechWorkerState
from src.schemas.speech_jobs import SpeechTtsJobCreate


def test_speech_job_exposes_queue_and_lease_fields():
    columns = SpeechJob.__table__.columns
    for name in (
        "operation", "status", "stage", "progress_percent",
        "requested_config_json", "resolved_config_json", "worker_id",
        "lease_expires_at", "heartbeat_at", "cancel_requested_at",
        "result_json", "error_code", "error_message",
    ):
        assert name in columns


def test_speech_job_exposes_retry_and_archive_metadata():
    columns = SpeechJob.__table__.columns
    assert "retry_of_job_id" in columns
    assert "archived_at" in columns


def test_tts_create_payload_is_typed_and_serializable():
    payload = SpeechTtsJobCreate(
        text="Olá mundo",
        engine="kokoro",
        voice="pt_br_dora",
        output_format="wav",
        speed=1.1,
        language="pt-br",
        normalize_ptbr=True,
        analyze_ptbr=True,
        preview=False,
    )
    dumped = payload.model_dump()
    assert dumped["text"] == "Olá mundo"
    assert dumped["engine"] == "kokoro"
    assert dumped["output_format"] == "wav"
    assert dumped["speed"] == 1.1


def test_speech_preset_exposes_native_config_storage():
    columns = SpeechPreset.__table__.columns
    assert "operation" in columns
    assert "config_json" in columns
    assert "is_builtin" in columns


def test_speech_preset_is_unique_per_operation_and_name():
    names = {constraint.name for constraint in SpeechPreset.__table__.constraints}
    assert "uq_speech_presets_operation_name" in names


def test_speech_artifact_links_to_job_and_has_type():
    columns = SpeechArtifact.__table__.columns
    assert "speech_job_id" in columns
    assert "artifact_type" in columns


def test_speech_artifact_job_foreign_key_does_not_delete_parent_job_from_artifact_side():
    fk = next(iter(SpeechArtifact.__table__.c.speech_job_id.foreign_keys))
    assert fk.ondelete == "CASCADE"
    relationship = inspect(SpeechArtifact).relationships.job
    assert "delete" not in relationship.cascade


def test_speaker_mapping_preserves_raw_label_separately():
    columns = SpeechSpeakerMapping.__table__.columns
    assert "raw_speaker" in columns
    assert "display_name" in columns


def test_speaker_mapping_does_not_mutate_raw_label_via_schema_storage():
    mapping = SpeechSpeakerMapping(raw_speaker="SPEAKER_00", display_name="Gabriel", speech_job_id=1)
    mapping.display_name = "João"
    assert mapping.raw_speaker == "SPEAKER_00"
    assert mapping.display_name == "João"


def test_worker_state_can_represent_idle_worker():
    columns = SpeechWorkerState.__table__.columns
    assert "worker_id" in columns
    assert "capabilities_json" in columns
    assert "last_heartbeat_at" in columns
