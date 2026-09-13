from pathlib import Path
import subprocess

import pytest

from speech_worker.stt.audio import convert_to_wav
from speech_worker.stt.errors import SttAudioConversionError, SttCancelled


def test_convert_to_wav_builds_expected_ffmpeg_command(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"media")
    output = tmp_path / "work" / "input.wav"
    captured = {}

    def runner(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output.write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0)

    result = convert_to_wav(source, output, runner=runner)
    assert result == output
    assert captured["command"] == [
        "ffmpeg", "-y", "-i", str(source), "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", str(output),
    ]
    assert captured["kwargs"]["check"] is True


def test_convert_to_wav_rejects_missing_input(tmp_path):
    with pytest.raises(SttAudioConversionError):
        convert_to_wav(tmp_path / "missing.mp3", tmp_path / "out.wav")


def test_convert_to_wav_maps_ffmpeg_failure(tmp_path):
    source = tmp_path / "input.mp3"
    source.write_bytes(b"x")

    def runner(command, **kwargs):
        raise subprocess.CalledProcessError(1, command, stderr="bad input")

    with pytest.raises(SttAudioConversionError, match="bad input"):
        convert_to_wav(source, tmp_path / "out.wav", runner=runner)


def test_convert_to_wav_honors_cancellation_before_process(tmp_path):
    source = tmp_path / "input.mp3"
    source.write_bytes(b"x")
    with pytest.raises(SttCancelled):
        convert_to_wav(source, tmp_path / "out.wav", cancel_check=lambda: True)
