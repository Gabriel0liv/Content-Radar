from types import SimpleNamespace

from src.services.speech_result_importer import SpeechResultImporter
from src.services.speech_storage import SpeechStorage


class FakeScalarResult:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeDb:
    def __init__(self):
        self.added = []
        self.commits = 0

    def execute(self, statement):
        return FakeScalarResult(None)

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def refresh(self, value):
        return None


def _result():
    return {
        "kind": "stt",
        "normalized": {
            "language": "pt",
            "engine": "whisperx",
            "model": "medium",
            "full_text": "Olá mundo",
            "diarized": True,
            "alignment_used": True,
            "warnings": [],
            "raw_metadata": {},
            "segments": [
                {
                    "index": 0,
                    "start": 0.0,
                    "end": 1.0,
                    "text": "Olá mundo",
                    "speaker": "SPEAKER_00",
                    "words": [
                        {"word": "Olá", "start": 0.0, "end": 0.4, "score": 0.9, "speaker": "SPEAKER_00"}
                    ],
                }
            ],
        },
        "artifacts": [],
    }


def test_finalize_stt_without_reference_only_persists_artifacts(tmp_path):
    db = FakeDb()
    importer = SpeechResultImporter(db, SpeechStorage(tmp_path))
    job = SimpleNamespace(id=5, reference_source_id=None, transcript_id=None)
    assert importer.finalize_stt(job, _result()) is None


def test_finalize_linked_stt_creates_whisperx_transcript(monkeypatch, tmp_path):
    db = FakeDb()
    captured = {}

    class FakeReferencesService:
        def __init__(self, db_arg):
            assert db_arg is db

        def create_manual_transcript(self, source_id, payload, job_id=None):
            captured["source_id"] = source_id
            captured["payload"] = payload
            captured["job_id"] = job_id
            return SimpleNamespace(id=77)

    monkeypatch.setattr("src.services.speech_result_importer.ReferencesService", FakeReferencesService)
    importer = SpeechResultImporter(db, SpeechStorage(tmp_path))
    job = SimpleNamespace(id=5, reference_source_id=10, transcript_id=None)

    transcript_id = importer.finalize_stt(job, _result())

    assert transcript_id == 77
    assert job.transcript_id == 77
    assert captured["source_id"] == 10
    assert captured["payload"].source_method == "whisperx"
    assert captured["payload"].segments[0].speaker == "SPEAKER_00"
    assert captured["payload"].segments[0].tokens_json["words"][0]["word"] == "Olá"


def test_finalize_is_idempotent_when_job_already_has_transcript(tmp_path):
    db = FakeDb()
    importer = SpeechResultImporter(db, SpeechStorage(tmp_path))
    job = SimpleNamespace(id=5, reference_source_id=10, transcript_id=77)
    assert importer.finalize_stt(job, _result()) == 77
