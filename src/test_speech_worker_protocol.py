from types import SimpleNamespace

import pytest

from src.services.speech_worker_protocol import JobCancelled, UnsupportedOperationError, WorkerCapabilities, clamp_progress
from speech_worker.runtime.executor import SpeechExecutor


def test_capability_payload_has_stable_shape():
    payload = WorkerCapabilities(worker_id="w1").as_dict()
    assert payload["worker_id"] == "w1"
    assert payload["cpu_available"] is True
    assert "ffmpeg_available" in payload
    assert "whisperx_available" in payload
    assert "torch_available" in payload
    assert "stt_ready" in payload
    assert "tts_engines" in payload


def test_worker_heartbeat_progress_is_clamped_0_100():
    assert clamp_progress(-10) == 0
    assert clamp_progress(55.9) == 55
    assert clamp_progress(200) == 100


def test_worker_stops_execution_when_cancel_requested():
    executor = SpeechExecutor()
    job = SimpleNamespace(operation="stt")
    with pytest.raises(JobCancelled):
        executor.execute(job, lambda *_: None, lambda: True)


def test_executor_rejects_non_stt_operation():
    executor = SpeechExecutor()
    job = SimpleNamespace(operation="tts")
    with pytest.raises(UnsupportedOperationError):
        executor.execute(job, lambda *_: None, lambda: False)
