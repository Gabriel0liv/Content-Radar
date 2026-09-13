from types import SimpleNamespace

import pytest

from speech_worker.stt.engine import WhisperXSttEngine
from speech_worker.stt.errors import SttCancelled, SttNoSpeech
from speech_worker.stt.types import SttResolvedConfig


class FakeCuda:
    @staticmethod
    def is_available():
        return False

    @staticmethod
    def empty_cache():
        return None


class FakeTorch:
    cuda = FakeCuda()


class FakeAsrModel:
    def __init__(self, result):
        self.result = result

    def transcribe(self, path, batch_size, language):
        return self.result


class FakeWhisperX:
    def __init__(self, result, *, alignment_error=None):
        self.result = result
        self.alignment_error = alignment_error
        self.load_model_kwargs = None

    def load_model(self, model, device, **kwargs):
        self.load_model_kwargs = (model, device, kwargs)
        return FakeAsrModel(self.result)

    def load_align_model(self, language_code, device):
        if self.alignment_error:
            raise self.alignment_error
        return object(), {"language": language_code}

    def align(self, segments, model, metadata, audio, device, return_char_alignments=False):
        return {"language": self.result.get("language"), "segments": segments}


def _config(**overrides):
    data = {
        "model": "medium",
        "language": "pt",
        "device": "auto",
        "compute_type": "int8",
        "batch_size": 2,
        "no_diarization": True,
        "vad_onset": 0.5,
        "vad_offset": 0.363,
    }
    data.update(overrides)
    return SttResolvedConfig(**data)


def test_engine_transcribes_and_aligns_without_importing_real_ml(monkeypatch, tmp_path):
    fake = FakeWhisperX({"language": "pt", "segments": [{"start": 0.0, "end": 1.0, "text": "olá"}]})
    engine = WhisperXSttEngine(hf_token=None)
    monkeypatch.setattr(engine, "_lazy_imports", lambda: (FakeTorch(), fake))
    progress = []

    result = engine.transcribe(tmp_path / "input.wav", _config(), lambda *args: progress.append(args), lambda: False)

    assert result.full_text == "olá"
    assert result.alignment_used is True
    assert result.diarized is False
    assert fake.load_model_kwargs[1] == "cpu"
    assert any(stage == "transcribing" for stage, _, _ in progress)


def test_alignment_failure_degrades_to_raw_transcript(monkeypatch, tmp_path):
    fake = FakeWhisperX(
        {"language": "pt", "segments": [{"start": 0.0, "end": 1.0, "text": "fala"}]},
        alignment_error=RuntimeError("align unavailable"),
    )
    engine = WhisperXSttEngine(hf_token=None)
    monkeypatch.setattr(engine, "_lazy_imports", lambda: (FakeTorch(), fake))

    result = engine.transcribe(tmp_path / "input.wav", _config(), lambda *args: None, lambda: False)
    assert result.full_text == "fala"
    assert result.alignment_used is False
    assert any("Alinhamento indisponível" in warning for warning in result.warnings)


def test_missing_hf_token_skips_requested_diarization(monkeypatch, tmp_path):
    fake = FakeWhisperX({"language": "pt", "segments": [{"start": 0.0, "end": 1.0, "text": "fala"}]})
    engine = WhisperXSttEngine(hf_token="")
    monkeypatch.setattr(engine, "_lazy_imports", lambda: (FakeTorch(), fake))

    result = engine.transcribe(
        tmp_path / "input.wav",
        _config(no_diarization=False),
        lambda *args: None,
        lambda: False,
    )
    assert result.diarized is False
    assert any("HF_TOKEN" in warning for warning in result.warnings)


def test_no_speech_raises_typed_error(monkeypatch, tmp_path):
    fake = FakeWhisperX({"language": "pt", "segments": []})
    engine = WhisperXSttEngine()
    monkeypatch.setattr(engine, "_lazy_imports", lambda: (FakeTorch(), fake))
    with pytest.raises(SttNoSpeech):
        engine.transcribe(tmp_path / "input.wav", _config(), lambda *args: None, lambda: False)


def test_cancellation_before_model_load_short_circuits(monkeypatch, tmp_path):
    engine = WhisperXSttEngine()
    monkeypatch.setattr(engine, "_lazy_imports", lambda: (_ for _ in ()).throw(AssertionError("should not import")))
    with pytest.raises(SttCancelled):
        engine.transcribe(tmp_path / "input.wav", _config(), lambda *args: None, lambda: True)
