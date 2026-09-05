from __future__ import annotations

import os
from pathlib import Path

from src.services.speech_storage import SpeechStorage
from src.services.speech_worker_protocol import JobCancelled, UnsupportedOperationError
from speech_worker.stt.audio import convert_to_wav
from speech_worker.stt.engine import WhisperXSttEngine
from speech_worker.stt.errors import SttCancelled
from speech_worker.stt.subtitles import cards_from_segments, render_json, render_srt, render_txt, render_vtt
from speech_worker.stt.types import SttResolvedConfig


_ARTIFACT_META = {
    "json": ("application/json", "json"),
    "txt": ("text/plain; charset=utf-8", "txt"),
    "srt": ("application/x-subrip; charset=utf-8", "srt"),
    "vtt": ("text/vtt; charset=utf-8", "vtt"),
}


class SpeechExecutor:
    def __init__(
        self,
        *,
        storage: SpeechStorage | None = None,
        engine: WhisperXSttEngine | None = None,
    ) -> None:
        self.storage = storage or SpeechStorage(os.getenv("SPEECH_DATA_ROOT", "data/speech"))
        self.engine = engine or WhisperXSttEngine()

    def execute(self, job, progress_callback, cancel_check) -> dict:
        if cancel_check():
            raise JobCancelled("Job cancelado antes da execução")
        if getattr(job, "operation", None) != "stt":
            raise UnsupportedOperationError(f"Operação {getattr(job, 'operation', None)!r} ainda não possui engine instalada")
        return self._execute_stt(job, progress_callback, cancel_check)

    def _execute_stt(self, job, progress_callback, cancel_check) -> dict:
        if not getattr(job, "input_path", None):
            raise ValueError("Job STT não possui arquivo de entrada")
        input_path = Path(job.input_path).resolve()
        self.storage.safe_storage_key(input_path)
        if not input_path.is_file():
            raise ValueError("Arquivo de entrada do job não existe")

        config = SttResolvedConfig.model_validate(job.resolved_config_json or {})
        work_wav = self.storage.work_dir(job.id) / "input.wav"
        keep_work = os.getenv("SPEECH_KEEP_WORK_FILES", "false").lower() == "true"

        progress_callback("preparing_audio", 5, "Preparando áudio")
        try:
            convert_to_wav(
                input_path,
                work_wav,
                cancel_check=cancel_check,
            )
            result = self.engine.transcribe(
                work_wav,
                config,
                progress_callback,
                cancel_check,
            )
            if cancel_check():
                raise JobCancelled("Job cancelado antes da exportação")

            progress_callback("exporting", 95, "Gerando arquivos")
            payload = result.model_dump(mode="json")
            segment_dicts = [segment.model_dump(mode="json") for segment in result.segments]
            cards = cards_from_segments(segment_dicts)
            requested_formats = {part.lower() for part in config.formats.split() if part.lower() in _ARTIFACT_META}
            artifacts: list[dict] = []

            renderers = {
                "json": lambda: render_json(payload),
                "txt": lambda: render_txt(segment_dicts),
                "srt": lambda: render_srt(cards, show_speaker=result.diarized),
                "vtt": lambda: render_vtt(cards, show_speaker=result.diarized),
            }
            for format_name in ("json", "txt", "srt", "vtt"):
                if format_name not in requested_formats:
                    continue
                mime_type, extension = _ARTIFACT_META[format_name]
                filename = f"transcript.{extension}"
                path = self.storage.artifact_path(job.id, filename)
                path.write_text(renderers[format_name](), encoding="utf-8")
                artifacts.append(
                    {
                        "artifact_type": format_name,
                        "storage_key": self.storage.safe_storage_key(path),
                        "filename": filename,
                        "mime_type": mime_type,
                        "size_bytes": path.stat().st_size,
                    }
                )

            progress_callback("finalizing", 99, "Finalizando transcrição")
            return {
                "kind": "stt",
                "normalized": payload,
                "artifacts": artifacts,
            }
        except SttCancelled as exc:
            raise JobCancelled(str(exc)) from exc
        finally:
            if not keep_work:
                work_wav.unlink(missing_ok=True)
