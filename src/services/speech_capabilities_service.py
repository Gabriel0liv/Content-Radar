from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.repositories.speech_jobs import SpeechJobRepository
from speech_worker.runtime.diagnostics import build_diagnostics


class SpeechCapabilitiesService:
    def __init__(self, db: Session) -> None:
        self.repo = SpeechJobRepository(db)

    @staticmethod
    def _is_online(state: Any, stale_after_seconds: int) -> bool:
        if state is None or state.last_heartbeat_at is None:
            return False
        heartbeat = state.last_heartbeat_at
        if heartbeat.tzinfo is None:
            heartbeat = heartbeat.replace(tzinfo=timezone.utc)
        return heartbeat >= datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)

    def get_capabilities(self, *, stale_after_seconds: int = 90) -> dict[str, Any]:
        state = self.repo.latest_worker_state()
        capabilities = dict(state.capabilities_json or {}) if state is not None else {}
        return {
            "worker_online": self._is_online(state, stale_after_seconds),
            "worker_id": state.worker_id if state is not None else None,
            "last_heartbeat_at": state.last_heartbeat_at if state is not None else None,
            "capabilities": capabilities,
        }

    def get_diagnostics(self, *, stale_after_seconds: int = 90) -> dict[str, Any]:
        payload = self.get_capabilities(stale_after_seconds=stale_after_seconds)
        if not payload["capabilities"]:
            diagnostics = {
                "status": "error",
                "checks": [
                    {
                        "id": "worker",
                        "status": "error",
                        "reason": "Nenhum estado de speech worker foi registrado.",
                        "action": "Inicie o speech worker para publicar capacidades e diagnósticos.",
                    }
                ],
            }
        else:
            diagnostics = build_diagnostics(payload["capabilities"])
            diagnostics["checks"].insert(
                0,
                {
                    "id": "worker",
                    "status": "ok" if payload["worker_online"] else "error",
                    "reason": "Speech worker online." if payload["worker_online"] else "Speech worker sem heartbeat recente.",
                    "action": None if payload["worker_online"] else "Verifique se o speech worker está em execução e conectado ao PostgreSQL.",
                },
            )
            if not payload["worker_online"]:
                diagnostics["status"] = "error"
        return {**payload, "diagnostics": diagnostics}
