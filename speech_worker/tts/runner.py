from __future__ import annotations

import json
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any, Callable

from src.services.speech_assets_service import SpeechAssetsService
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


def _artifact(storage: SpeechStorage, path: Path, artifact_type: str, mime_type: str, **extra: Any) -> dict[str, Any]:
    payload = {
        "artifact_type": artifact_type,
        "storage_key": storage.safe_storage_key(path),
        "filename": path.name,
        "mime_type": mime_type,
        "size_bytes": path.stat().st_size,
    }
    payload.update(extra)
    return payload


class TTSRunner:
    def __init__(self, *, storage: SpeechStorage, registry: TTSRegistry | None = None) -> None:
        self.storage = storage
        self.registry = registry or TTSRegistry()

    def run(self, job: Any, progress_callback: ProgressCallback, cancel_check: CancelCheck) -> dict[str, Any]:
        if cancel_check():
            raise JobCancelled("Job TTS cancelado antes da execução")

        config = dict(getattr(job, "resolved_config_json", None) or {})
        if config.get("mode") == "voice_compare":
            return self._run_voice_compare(job, config, progress_callback, cancel_check)
        return self._run_synthesis(job, config, progress_callback, cancel_check)

    def _run_synthesis(
        self,
        job: Any,
        config: dict[str, Any],
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> dict[str, Any]:
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

            artifacts = [_artifact(self.storage, output_path, "audio", mime_type)]
            kind = "tts"
            if config.get("mode") == "voice_sample":
                if output_format != "wav":
                    raise ValueError("Amostras de voz devem ser geradas em WAV")
                sample_path = SpeechAssetsService(self.storage).sample_path(voice)
                shutil.copyfile(output_path, sample_path)
                artifacts.append(
                    _artifact(
                        self.storage,
                        sample_path,
                        "voice_sample",
                        "audio/wav",
                        voice_id=voice,
                        engine=engine_name,
                    )
                )
                kind = "tts_voice_sample"

            progress_callback("finalizing", 99, "Finalizando áudio")
            return {
                "kind": kind,
                "engine": engine_name,
                "voice": voice,
                "preview": bool(config.get("preview")),
                "artifacts": artifacts,
            }
        finally:
            for path in fragment_paths:
                path.unlink(missing_ok=True)
            merged_wav.unlink(missing_ok=True)

    def _run_voice_compare(
        self,
        job: Any,
        config: dict[str, Any],
        progress_callback: ProgressCallback,
        cancel_check: CancelCheck,
    ) -> dict[str, Any]:
        text = str(config.get("effective_text") or "").strip()
        if not text:
            raise ValueError("Comparação de vozes exige texto")

        language = str(config.get("language") or "pt-br")
        requested_ids = {str(value) for value in (config.get("voice_ids") or []) if str(value).strip()}
        voices = [
            voice
            for voice in self.registry.list_voices(language=language)
            if not requested_ids or str(voice.get("id")) in requested_ids
        ]
        if not voices:
            raise ValueError("Nenhuma voz disponível para comparação")

        progress_callback("preparing", 5, "Preparando comparação de vozes")
        total = len(voices)
        results: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []

        for index, voice in enumerate(voices, start=1):
            if cancel_check():
                raise JobCancelled("Comparação de vozes cancelada")
            voice_id = str(voice.get("id") or "")
            engine_name = str(voice.get("engine") or "")
            progress = 10 + int((index - 1) / max(total, 1) * 70)
            progress_callback("voice", progress, f"Gerando voz {index} de {total}: {voice_id}")
            output_path = self.storage.artifact_path(int(job.id), f"compare_{voice_id}.wav")
            try:
                if voice.get("available") is False:
                    raise RuntimeError(str(voice.get("unavailable_reason") or "voz indisponível"))
                engine = self.registry.create_engine(
                    engine_name,
                    voice_id,
                    device=str(config.get("device") or "cpu"),
                    cache_dir=config.get("cache_dir"),
                    speed=float(config.get("speed", 1.0)),
                    offline=bool(config.get("offline", False)),
                )
                engine.synthesize(text, output_path, output_format="wav")
                audio_artifact = _artifact(
                    self.storage,
                    output_path,
                    "voice_compare_audio",
                    "audio/wav",
                    voice_id=voice_id,
                    engine=engine_name,
                )
                artifacts.append(audio_artifact)
                results.append(
                    {
                        "voice_id": voice_id,
                        "engine": engine_name,
                        "status": "success",
                        "storage_key": audio_artifact["storage_key"],
                        "error": None,
                    }
                )
            except JobCancelled:
                raise
            except Exception as exc:
                output_path.unlink(missing_ok=True)
                results.append(
                    {
                        "voice_id": voice_id,
                        "engine": engine_name,
                        "status": "failed",
                        "storage_key": None,
                        "error": str(exc),
                    }
                )

        if cancel_check():
            raise JobCancelled("Comparação de vozes cancelada antes dos relatórios")
        progress_callback("exporting", 90, "Gerando relatórios da comparação")
        report_payload = {"text": text, "language": language, "results": results}
        json_path = self.storage.artifact_path(int(job.id), "voice_compare_report.json")
        json_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        artifacts.append(_artifact(self.storage, json_path, "voice_compare_json", "application/json"))

        if bool(config.get("compare_report_markdown", True)):
            markdown_path = self.storage.artifact_path(int(job.id), "voice_compare_report.md")
            lines = [
                "# Comparação de vozes PT-BR",
                "",
                f"Texto: {text}",
                "",
                "| Voz | Motor | Status | Erro |",
                "| --- | --- | --- | --- |",
            ]
            for item in results:
                lines.append(
                    f"| {item['voice_id']} | {item['engine']} | {item['status']} | {item['error'] or ''} |"
                )
            markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            artifacts.append(_artifact(self.storage, markdown_path, "voice_compare_markdown", "text/markdown; charset=utf-8"))

        progress_callback("finalizing", 99, "Finalizando comparação de vozes")
        return {
            "kind": "tts_voice_compare",
            "results": results,
            "artifacts": artifacts,
        }
