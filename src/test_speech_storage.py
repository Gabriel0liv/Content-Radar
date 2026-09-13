import pytest

from src.services.speech_storage import SpeechStorage


def test_job_dir_is_scoped_under_root(tmp_path):
    storage = SpeechStorage(tmp_path)
    path = storage.job_dir(42)
    assert path == tmp_path.resolve() / "jobs" / "42"


def test_artifact_filename_cannot_escape_job_dir(tmp_path):
    storage = SpeechStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.artifact_path(1, "../../secret.txt")


def test_safe_storage_key_is_relative_to_root(tmp_path):
    storage = SpeechStorage(tmp_path)
    path = storage.artifact_path(3, "result.srt")
    assert storage.safe_storage_key(path) == "jobs/3/artifacts/result.srt"


def test_save_input_writes_only_to_managed_input_dir(tmp_path):
    storage = SpeechStorage(tmp_path)
    path = storage.save_input(7, "sample.wav", [b"abc", b"def"])
    assert path == tmp_path.resolve() / "jobs" / "7" / "input" / "sample.wav"
    assert path.read_bytes() == b"abcdef"


def test_stage_input_finishes_inside_managed_inputs_root(tmp_path):
    storage = SpeechStorage(tmp_path)
    path = storage.stage_input("voice.mp3", [b"one", b"two"])
    assert path.read_bytes() == b"onetwo"
    assert path.name == "voice.mp3"
    assert path.parent.parent == tmp_path.resolve() / "inputs"
    assert storage.safe_storage_key(path).startswith("inputs/")


def test_stage_input_rejects_path_traversal(tmp_path):
    storage = SpeechStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.stage_input("../voice.mp3", [b"x"])
