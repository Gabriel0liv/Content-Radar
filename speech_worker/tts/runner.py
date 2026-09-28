from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any, Callable

from src.services.speech_storage import SpeechStorage
from src.services.speech_worker_protocol import JobCancelled
from speech_worker.tts.registry import TTSRegistry
from speech_worker.tts.text_chunking import chunk_text


ProgressCallback = Callable[[str, int, str], None]
CancelCheck = Callable[[], bool]


def _merge_wav_files(paths: list[Path], destination: Path) -> None:
    if not paths:
        raise ValueError("nenhum fragmento TTS para mesclar")
    params = None
    frames: list[bytes] = []
    for path in paths:
        with wave.open(str(path), "rb") as reader:
            current = (reader.getnchannels(), reader.getsampwidth(), reader.getframerate(), reader.getcomptype())
            if params is None:
                params = current
            elif current != params:
                raise ValueError("fragmentos TTS possuem formatos WAV incompatíveis")
            frames.append(reader.readframes(reader.getnframes()))
    assert params is not None
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as writer:
        writer.setnchannels(params[0])
        writer.setsampwidth(params[1])
        writer.setframerate(params[2])
        writer.setcomptype(params[3], "not compressed")
        for frame in frames:
            writer.writeframes(frame)


def _wav_to_mp3(source: Path, destination: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg não encontrado para exportar MP3")
    process = subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(source), str(destination)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0 or not destination.exists():
        raise RuntimeError("FFmpeg falhou ao exportar MP3")


class TTSRunner:
    def __init__(self, *, storage: SpeechStorage, registry: TTSRegistry | None = None) -> None:
        self.storage = storage
        self.registry = registry or TTSRegistry()

    def run(self, job: Any, progress_callback: ProgressCallback, cancel_check: CancelCheck) -> dict[str, Any]:
        if cancel_check():
            raise JobCancelled("Job TTS cancelado antes da execução")

        config = dict(getattr(job, "resolved_config_json", None) or {})
        engine_name = str(config.get("engine") or "").strip().lower()
        voice = str(config.get("voice") or "").strip()
        text = str(config.get("effective_text") or "")
        output_format = str(config.get("output_format") or "wav").lower()
        if not engine_name or not voice or not text.strip():
            raise ValueError("Job TTS possui configuração incompleta")
        if output_format not in {"wav", "mp3"}:
            raise ValueError("Formato TTS inválido")

        progress_callback("preparing", 5, "Preparando síntese de voz")
        engine = self.registry.create_engine(
            engine_name,
            voice,
            device=str(config.get("device") or "cpu"),
            cache_dir=config.get("cache_dir"),
            speed=float(config.get("speed", 1.0)),
            offline=bool(config.get("offline", False)),
        )
        chunks = chunk_text(text, max_chars=int(config.get("chunk_chars", 400)))
        if not chunks:
            raise ValueError("Texto TTS vazio após preparação")

        work_dir = self.storage.work_dir(int(job.id))
        fragment_paths: list[Path] = []
        merged_wav = work_dir / "merged.wav"
        output_name = "preview" if bool(config.get("preview")) else "speech"
        output_path = self.storage.artifact_path(int(job.id), f"{output_name}.{output_format}")

        try:
            total = len(chunks)
            for index, chunk in enumerate(chunks, start=1):
                if cancel_check():
                    raise JobCancelled("Job TTS cancelado durante geração")
                progress = 10 + int((index - 1) / max(total, 1) * 75)
                progress_callback("chunk", progress, f"Gerando fragmento {index} de {total}")
                fragment = work_dir / f"chunk_{index:04d}.wav"
                engine.synthesize(chunk, fragment, output_format="wav")
                fragment_paths.append(fragment)

            if cancel_check():
                raise JobCancelled("Job TTS cancelado antes da exportação")
            progress_callback("exporting", 90, "Mesclando e exportando áudio")
            _merge_wav_files(fragment_paths, merged_wav)
            if output_format == "wav":
                shutil.copyfile(merged_wav, output_path)
                mime_type = "audio/wav"
            else:
                _wav_to_mp3(merged_wav, output_path)
                mime_type = "audio/mpeg"

            progress_callback("finalizing", 99, "Finalizando áudio")
            return {
                "kind": "tts",
                "engine": engine_name,
                "voice": voice,
                "preview": bool(config.get("preview")),
                "artifacts": [
                    {
                        "artifact_type": "audio",
                        "storage_key": self.storage.safe_storage_key(output_path),
                        "filename": output_path.name,
                        "mime_type": mime_type,
                        "size_bytes": output_path.stat().st_size,
                    }
                ],
            }
        finally:
            for path in fragment_paths:
                path.unlink(missing_ok=True)
            merged_wav.unlink(missing_ok=True)
