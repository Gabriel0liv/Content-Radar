from src.models.speech import SpeechArtifact, SpeechJob, SpeechPreset, SpeechSpeakerMapping, SpeechWorkerState


def test_speech_job_exposes_queue_and_lease_fields():
    columns = SpeechJob.__table__.columns
    for name in (
        "operation", "status", "stage", "progress_percent",
        "requested_config_json", "resolved_config_json", "worker_id",
        "lease_expires_at", "heartbeat_at", "cancel_requested_at",
        "result_json", "error_code", "error_message",
    ):
        assert name in columns


def test_speech_preset_exposes_native_config_storage():
    columns = SpeechPreset.__table__.columns
    assert "operation" in columns
    assert "config_json" in columns
    assert "is_builtin" in columns


def test_speech_artifact_links_to_job():
    assert "speech_job_id" in SpeechArtifact.__table__.columns


def test_speaker_mapping_preserves_raw_label_separately():
    columns = SpeechSpeakerMapping.__table__.columns
    assert "raw_speaker" in columns
    assert "display_name" in columns


def test_worker_state_can_represent_idle_worker():
    columns = SpeechWorkerState.__table__.columns
    assert "worker_id" in columns
    assert "capabilities_json" in columns
    assert "last_heartbeat_at" in columns
