from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from src.models.reference import ReferenceSource
from src.repositories.speech_jobs import SpeechJobRepository
from src.schemas.speech import SpeechSttOptions
from src.schemas.speech_jobs import SpeechSttJobCreate
from src.services.speech_presets import resolve_stt_config
from src.services.speech_storage import SpeechStorage


class SpeechReferenceNotFoundError(ValueError):
    pass


class SpeechJobsService:
    def __init__(self, db: Session, storage: SpeechStorage | None = None) -> None:
        self.db = db
        self.repo = SpeechJobRepository(db)
        self.storage = storage or SpeechStorage(os.getenv("SPEECH_DATA_ROOT", "data/speech"))

    def _validate_reference(self, reference_source_id: int | None) -> None:
        if reference_source_id is not None and self.db.get(ReferenceSource, reference_source_id) is None:
            raise SpeechReferenceNotFoundError("Referência não encontrada")

    @staticmethod
    def _resolve_request(request: SpeechSttJobCreate) -> tuple[dict, dict]:
        requested = request.model_dump(exclude_none=True)
        options = SpeechSttOptions(
            preset=request.preset,
            language=request.language,
            identify_speakers=request.diarization,
            num_speakers=request.num_speakers,
            min_speakers=request.min_speakers,
            max_speakers=request.max_speakers,
            quiet_speech=request.quiet_speech,
            initial_prompt=request.initial_prompt,
        )
        resolved = resolve_stt_config(options).model_dump(exclude_none=True)
        resolved["diarize_model"] = os.getenv("SPEECH_DIARIZE_MODEL", "pyannote/speaker-diarization-3.1")
        return requested, resolved

    def create_stt_job(self, request: SpeechSttJobCreate):
        self._validate_reference(request.reference_source_id)
        requested, resolved = self._resolve_request(request)
        return self.repo.create(
            operation="stt",
            requested_config_json=requested,
            resolved_config_json=resolved,
            input_path=None,
            reference_source_id=request.reference_source_id,
        )

    def create_uploaded_stt_job(
        self,
        request: SpeechSttJobCreate,
        *,
        filename: str,
        chunks: Iterable[bytes],
    ):
        self._validate_reference(request.reference_source_id)
        requested, resolved = self._resolve_request(request)
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

    def get_job(self, job_id: int):
        return self.repo.get(job_id)

    def list_jobs(self, limit: int = 50):
        return self.repo.list_recent(limit=max(1, min(200, limit)))

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
