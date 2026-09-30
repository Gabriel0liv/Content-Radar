from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from sqlalchemy.orm import Session

from src.models.reference import ReferenceSource
from src.repositories.speech_jobs import SpeechJobRepository
from src.schemas.speech_jobs import SpeechSttJobCreate, SpeechTtsJobCreate
from src.services.speech_assets_service import SpeechAssetsService
from src.services.speech_presets_service import SpeechPresetsService
from src.services.speech_storage import SpeechStorage
from speech_worker.tts.ptbr_text import analyze_ptbr_text, normalize_ptbr_text


_DEFAULT_VOICE_SAMPLE_TEXT = (
    "Olá! Esta é uma amostra de voz em português do Brasil para comparar ritmo, "
    "clareza, entonação e naturalidade."
)


class SpeechReferenceNotFoundError(ValueError):
    pass


class SpeechJobsService:
    def __init__(self, db: Session, storage: SpeechStorage | None = None) -> None:
        self.db = db
        self.repo = SpeechJobRepository(db)
        self.presets = SpeechPresetsService(db)
        self.storage = storage or SpeechStorage(os.getenv("SPEECH_DATA_ROOT", "data/speech"))
        self.assets = SpeechAssetsService(self.storage)

    def _validate_reference(self, reference_source_id: int | None) -> None:
        if reference_source_id is not None and self.db.get(ReferenceSource, reference_source_id) is None:
            raise SpeechReferenceNotFoundError("Referência não encontrada")

    def _resolve_stt_request(self, request: SpeechSttJobCreate) -> tuple[dict[str, Any], dict[str, Any]]:
        requested = request.model_dump(exclude_none=True)
        base = self.presets.resolve_stt_preset(request.preset)
        resolved: dict[str, Any] = {
            "model": base.get("model", "medium"),
            "language": base.get("language"),
            "device": base.get("device", "auto"),
            "compute_type": base.get("compute_type", "int8"),
            "batch_size": base.get("batch_size", 2),
            "no_diarization": base.get("no_diarization", not request.diarization),
            "num_speakers": base.get("num_speakers"),
            "min_speakers": base.get("min_speakers"),
            "max_speakers": base.get("max_speakers"),
            "vad_onset": base.get("vad_onset", 0.5),
            "vad_offset": base.get("vad_offset", 0.363),
            "chunk_size": base.get("chunk_size", 30),
            "initial_prompt": base.get("initial_prompt"),
            "diarize_model": base.get("diarize_model") or os.getenv("SPEECH_DIARIZE_MODEL", "pyannote/speaker-diarization-3.1"),
            "offline": bool(base.get("offline", False)),
            "cache_dir": base.get("cache_dir") or os.getenv("HF_HOME"),
            "export_formats": list(base.get("export_formats") or ["txt", "json", "srt", "vtt"]),
        }
        resolved["language"] = request.language if request.language is not None else resolved["language"]
        resolved["no_diarization"] = not request.diarization
        resolved["num_speakers"] = request.num_speakers
        resolved["min_speakers"] = None if request.num_speakers is not None else request.min_speakers
        resolved["max_speakers"] = None if request.num_speakers is not None else request.max_speakers
        resolved["initial_prompt"] = request.initial_prompt if request.initial_prompt is not None else resolved["initial_prompt"]
        if request.quiet_speech:
            resolved["vad_onset"] = 0.1
            resolved["vad_offset"] = 0.1
        overrides = {
            "model": request.model,
            "device": request.device,
            "compute_type": request.compute_type,
            "batch_size": request.batch_size,
            "vad_onset": request.vad_onset,
            "vad_offset": request.vad_offset,
            "chunk_size": request.chunk_size,
            "diarize_model": request.diarize_model,
            "offline": request.offline,
            "cache_dir": request.cache_dir,
            "export_formats": request.export_formats,
        }
        for key, value in overrides.items():
            if value is not None:
                resolved[key] = value
        resolved["formats"] = " ".join(resolved["export_formats"])
        return requested, resolved

    def _resolve_tts_request(self, request: SpeechTtsJobCreate) -> tuple[dict[str, Any], dict[str, Any]]:
        requested = request.model_dump(exclude_none=True)
        base: dict[str, Any] = {}
        if request.preset:
            base = self.presets.resolve_tts_preset(request.preset)
        resolved = {
            "engine": request.engine or base.get("engine", "kokoro"),
            "voice": request.voice or base.get("voice", "pt_br_dora"),
            "output_format": request.output_format or base.get("output_format", "wav"),
            "speed": request.speed if request.speed is not None else float(base.get("speed", 1.0)),
            "language": request.language or base.get("language", "pt-br"),
            "normalize_ptbr": bool(request.normalize_ptbr),
            "analyze_ptbr": bool(request.analyze_ptbr),
            "preview": bool(request.preview),
            "preview_chars": int(request.preview_chars),
            "device": str(base.get("device") or os.getenv("SPEECH_TTS_DEVICE", "cpu")),
            "cache_dir": base.get("cache_dir") or os.getenv("SPEECH_TTS_CACHE"),
            "offline": bool(base.get("offline", False)),
            "chunk_chars": int(base.get("chunk_chars", 400)),
        }
        effective = request.text
        if resolved["normalize_ptbr"]:
            effective = normalize_ptbr_text(effective)
        if resolved["preview"]:
            effective = effective[: resolved["preview_chars"]].rstrip()
        resolved["effective_text"] = effective
        if resolved["analyze_ptbr"]:
            resolved["analysis"] = analyze_ptbr_text(request.text)
        return requested, resolved

    def create_stt_job(self, request: SpeechSttJobCreate):
        self._validate_reference(request.reference_source_id)
        requested, resolved = self._resolve_stt_request(request)
        return self.repo.create(
            operation="stt",
            requested_config_json=requested,
            resolved_config_json=resolved,
            input_path=None,
            reference_source_id=request.reference_source_id,
        )

    def create_uploaded_stt_job(self, request: SpeechSttJobCreate, *, filename: str, chunks: Iterable[bytes]):
        self._validate_reference(request.reference_source_id)
        requested, resolved = self._resolve_stt_request(request)
        staged_path = self.storage.stage_input(filename, chunks)
        try:
            return self.repo.create(
                operation="stt",
                requested_config_json=requested,
                resolved_config_json=resolved,
                input_path=str(staged_path),
                reference_source_id=request.reference_source_id,
            )
        except Exception:
            staged_path.unlink(missing_ok=True)
            try:
                staged_path.parent.rmdir()
            except OSError:
                pass
            raise

    def create_tts_job(self, request: SpeechTtsJobCreate):
        requested, resolved = self._resolve_tts_request(request)
        return self.repo.create(
            operation="tts",
            requested_config_json=requested,
            resolved_config_json=resolved,
            input_path=None,
            reference_source_id=None,
        )

    def create_voice_sample_job(self, voice_id: str, *, text: str | None = None):
        voice = self.assets.get_voice(voice_id)
        sample_text = (text or _DEFAULT_VOICE_SAMPLE_TEXT).strip()
        if not sample_text:
            raise ValueError("Texto da amostra não pode ser vazio")
        requested = {
            "mode": "voice_sample",
            "voice_id": voice_id,
            "text": sample_text,
        }
        resolved = {
            "mode": "voice_sample",
            "engine": voice["engine"],
            "voice": voice_id,
            "effective_text": sample_text,
            "output_format": "wav",
            "speed": 1.0,
            "language": voice["language"],
            "device": os.getenv("SPEECH_TTS_DEVICE", "cpu"),
            "cache_dir": os.getenv("SPEECH_TTS_CACHE"),
            "offline": False,
            "chunk_chars": 400,
        }
        return self.repo.create(
            operation="tts",
            requested_config_json=requested,
            resolved_config_json=resolved,
            input_path=None,
            reference_source_id=None,
        )

    def create_all_voice_sample_jobs(self, *, text: str | None = None) -> list[Any]:
        return [self.create_voice_sample_job(voice["id"], text=text) for voice in self.assets.list_voices()]

    def create_voice_compare_job(
        self,
        *,
        text: str,
        voice_ids: list[str] | None = None,
        language: str = "pt-br",
        markdown_report: bool = True,
    ):
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Texto da comparação não pode ser vazio")
        normalized_voice_ids: list[str] = []
        for voice_id in voice_ids or []:
            self.assets.get_voice(voice_id)
            if voice_id not in normalized_voice_ids:
                normalized_voice_ids.append(voice_id)
        requested = {
            "mode": "voice_compare",
            "text": clean_text,
            "voice_ids": normalized_voice_ids,
            "language": language,
            "markdown_report": markdown_report,
        }
        resolved = {
            "mode": "voice_compare",
            "effective_text": clean_text,
            "voice_ids": normalized_voice_ids,
            "language": language,
            "device": os.getenv("SPEECH_TTS_DEVICE", "cpu"),
            "cache_dir": os.getenv("SPEECH_TTS_CACHE"),
            "offline": False,
            "speed": 1.0,
            "compare_report_markdown": markdown_report,
        }
        return self.repo.create(
            operation="tts",
            requested_config_json=requested,
            resolved_config_json=resolved,
            input_path=None,
            reference_source_id=None,
        )

    def analyze_tts_text(self, text: str) -> dict[str, Any]:
        return analyze_ptbr_text(text)

    def get_job(self, job_id: int):
        return self.repo.get(job_id)

    def list_jobs(self, limit: int = 50, *, operation: str | None = None, status: str | None = None, include_archived: bool = False):
        return self.repo.list_recent(
            limit=max(1, min(200, limit)),
            operation=operation,
            status=status,
            include_archived=include_archived,
        )

    def cancel_job(self, job_id: int):
        return self.repo.request_cancel(job_id)

    def get_status(self, stale_after_seconds: int = 90) -> dict:
        state = self.repo.latest_worker_state()
        online = False
        if state is not None and state.last_heartbeat_at is not None:
            now = datetime.now(timezone.utc)
            heartbeat = state.last_heartbeat_at
            if heartbeat.tzinfo is None:
                heartbeat = heartbeat.replace(tzinfo=timezone.utc)
            online = heartbeat >= now - timedelta(seconds=stale_after_seconds)
        return {
            "mode": "native",
            "queue": self.repo.queue_counts(),
            "worker": {
                "online": online,
                "worker_id": state.worker_id if state else None,
                "last_heartbeat_at": state.last_heartbeat_at if state else None,
                "capabilities": state.capabilities_json if state else None,
            },
        }
