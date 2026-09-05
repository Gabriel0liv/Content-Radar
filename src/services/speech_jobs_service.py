from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.models.reference import ReferenceSource
from src.repositories.speech_jobs import SpeechJobRepository
from src.schemas.speech import SpeechSttOptions
from src.schemas.speech_jobs import SpeechSttJobCreate
from src.services.speech_presets import resolve_stt_config


class SpeechReferenceNotFoundError(ValueError):
    pass


class SpeechJobsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SpeechJobRepository(db)

    def create_stt_job(self, request: SpeechSttJobCreate):
        if request.reference_source_id is not None:
            if self.db.get(ReferenceSource, request.reference_source_id) is None:
                raise SpeechReferenceNotFoundError("Referência não encontrada")

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
        return self.repo.create(
            operation="stt",
            requested_config_json=requested,
            resolved_config_json=resolved,
            input_path=None,
            reference_source_id=request.reference_source_id,
        )

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
