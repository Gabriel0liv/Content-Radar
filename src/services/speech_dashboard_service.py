from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.speech import SpeechJob
from src.repositories.speech_jobs import SpeechJobRepository
from src.services.speech_assets_service import SpeechAssetsService
from src.services.speech_storage import SpeechStorage


class SpeechDashboardService:
    def __init__(
        self,
        db: Session,
        *,
        storage: SpeechStorage | None = None,
        repo: SpeechJobRepository | None = None,
        assets: SpeechAssetsService | None = None,
    ) -> None:
        self.db = db
        self.repo = repo or SpeechJobRepository(db)
        self.storage = storage or SpeechStorage("data/speech")
        self.assets = assets or SpeechAssetsService(self.storage)

    @staticmethod
    def _utc_day_start() -> datetime:
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _counts(self) -> dict[str, int]:
        since = self._utc_day_start()
        row = self.db.execute(
            select(
                func.count(SpeechJob.id).label("total_jobs"),
                func.count(SpeechJob.id).filter(SpeechJob.status == "completed").label("jobs_completed"),
                func.count(SpeechJob.id).filter(SpeechJob.status == "failed").label("jobs_failed"),
                func.count(SpeechJob.id).filter(
                    SpeechJob.operation == "stt", SpeechJob.created_at >= since
                ).label("transcriptions_today"),
                func.count(SpeechJob.id).filter(
                    SpeechJob.operation == "tts", SpeechJob.created_at >= since
                ).label("tts_today"),
            )
        ).one()
        return {
            "total_jobs": int(row.total_jobs or 0),
            "jobs_completed": int(row.jobs_completed or 0),
            "jobs_failed": int(row.jobs_failed or 0),
            "transcriptions_today": int(row.transcriptions_today or 0),
            "tts_today": int(row.tts_today or 0),
        }

    def _storage_used_bytes(self) -> int:
        total = 0
        try:
            for path in self.storage.root.rglob("*"):
                if path.is_file():
                    try:
                        total += path.stat().st_size
                    except OSError:
                        continue
        except OSError:
            return total
        return total

    @staticmethod
    def _job_label(job: Any) -> str:
        requested = dict(getattr(job, "requested_config_json", None) or {})
        if getattr(job, "operation", None) == "tts":
            text = str(requested.get("text") or "").strip().replace("\n", " ")
            if text:
                return text[:80]
            voice = str(requested.get("voice_id") or requested.get("voice") or "").strip()
            if voice:
                return f"Voz: {voice}"
            return f"TTS #{job.id}"
        return f"Transcrição #{job.id}"

    @classmethod
    def _recent_job(cls, job: Any) -> dict[str, Any]:
        return {
            "id": int(job.id),
            "operation": str(job.operation),
            "status": str(job.status),
            "stage": str(job.stage),
            "progress_percent": int(job.progress_percent or 0),
            "label": cls._job_label(job),
            "error_code": getattr(job, "error_code", None),
            "error_message": getattr(job, "error_message", None),
            "created_at": getattr(job, "created_at", None),
            "finished_at": getattr(job, "finished_at", None),
        }

    def get_dashboard(self) -> dict[str, Any]:
        counts = self._counts()
        state = self.repo.latest_worker_state()
        capabilities = dict(state.capabilities_json or {}) if state is not None else {}
        voices = self.assets.list_voices(capabilities=capabilities)
        available_voices = sum(1 for voice in voices if voice.get("available"))
        recent = self.repo.list_recent(limit=6)
        queue = self.repo.queue_counts()
        success_rate = round(
            counts["jobs_completed"] / counts["total_jobs"] * 100.0, 2
        ) if counts["total_jobs"] else 0.0
        active = next((job for job in recent if getattr(job, "status", None) == "running"), None)
        return {
            **counts,
            "success_rate": success_rate,
            "available_voices": available_voices,
            "storage_used_bytes": self._storage_used_bytes(),
            "queue": queue,
            "recent_jobs": [self._recent_job(job) for job in recent],
            "active_job": self._recent_job(active) if active is not None else None,
            "system_health": {
                "worker_online": state is not None,
                "cuda": bool(capabilities.get("cuda_available")),
                "gpu_name": capabilities.get("gpu_name"),
                "ffmpeg": bool(capabilities.get("ffmpeg_available")),
                "espeak": bool(capabilities.get("espeak_available")),
                "whisperx": bool(capabilities.get("whisperx_available")),
                "diarization": bool(capabilities.get("diarization_ready")),
                "hf_token_configured": bool(capabilities.get("hf_token_configured")),
                "tts_engines": capabilities.get("tts_engines") or [],
            },
        }
