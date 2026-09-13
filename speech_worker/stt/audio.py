from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from speech_worker.stt.errors import SttAudioConversionError, SttCancelled


Runner = Callable[..., subprocess.CompletedProcess]


def convert_to_wav(
    input_path: Path | str,
    output_path: Path | str,
    *,
    runner: Runner = subprocess.run,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    source = Path(input_path)
    destination = Path(output_path)

    if not source.is_file():
        raise SttAudioConversionError(f"Arquivo de entrada não encontrado: {source}")
    if cancel_check and cancel_check():
        raise SttCancelled("Job cancelado antes da conversão de áudio")

    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(destination),
    ]

    try:
        runner(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise SttAudioConversionError("FFmpeg não foi encontrado no worker") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise SttAudioConversionError(
            f"Falha ao converter áudio com FFmpeg{': ' + detail if detail else ''}"
        ) from exc

    if cancel_check and cancel_check():
        destination.unlink(missing_ok=True)
        raise SttCancelled("Job cancelado após a conversão de áudio")
    if not destination.exists():
        raise SttAudioConversionError("FFmpeg terminou sem produzir o WAV esperado")
    return destination
