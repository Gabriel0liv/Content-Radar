import json
import wave
from pathlib import Path
from types import SimpleNamespace

from src.services.speech_storage import SpeechStorage
from speech_worker.tts.runner import TTSRunner


class FakeEngine:
    def __init__(self, voice_id: str, *, fail: bool = False):
        self.voice_id = voice_id
        self.fail = fail

    def synthesize(self, text, output_path, output_format="wav"):
        if self.fail:
            raise RuntimeError(f"voice {self.voice_id} failed")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(16000)
            writer.writeframes(b"\x00\x00" * 160)
        return path


class FakeRegistry:
    def list_voices(self, **kwargs):
        return [
            {"id": "pt_br_dora", "engine": "kokoro", "available": True},
            {"id": "pt_br_faber", "engine": "piper", "available": True},
        ]

    def create_engine(self, name, voice_id, **kwargs):
        return FakeEngine(voice_id, fail=voice_id == "pt_br_faber")


def test_voice_compare_continues_after_individual_failure_and_writes_reports(tmp_path):
    storage = SpeechStorage(tmp_path)
    runner = TTSRunner(storage=storage, registry=FakeRegistry())
    progress = []
    job = SimpleNamespace(
        id=21,
        resolved_config_json={
            "mode": "voice_compare",
            "effective_text": "Olá mundo.",
            "language": "pt-br",
            "device": "cpu",
            "speed": 1.0,
            "compare_report_markdown": True,
        },
    )

    result = runner.run(job, lambda stage, pct, msg: progress.append((stage, pct, msg)), lambda: False)

    assert result["kind"] == "tts_voice_compare"
    assert [item["status"] for item in result["results"]] == ["success", "failed"]
    assert any(stage == "voice" and "1 de 2" in message for stage, _, message in progress)
    assert any(stage == "voice" and "2 de 2" in message for stage, _, message in progress)

    artifacts = {item["artifact_type"]: item for item in result["artifacts"]}
    assert "voice_compare_json" in artifacts
    assert "voice_compare_markdown" in artifacts
    report = json.loads((storage.root / artifacts["voice_compare_json"]["storage_key"]).read_text(encoding="utf-8"))
    assert report["results"][0]["voice_id"] == "pt_br_dora"
    assert report["results"][1]["error"] == "voice pt_br_faber failed"
