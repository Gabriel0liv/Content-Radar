from __future__ import annotations

import os
import time

import src.db.base  # noqa: F401  # register all SQLAlchemy models before mapper configuration
from src.case_radar.orchestrator import CaseRadarCancelled, CaseRadarOrchestrator
from src.case_radar.providers.registry import build_default_registry
from src.db.session import SessionLocal
from src.repositories.case_radar import CaseRadarRepository


def run_once(
    repo: CaseRadarRepository,
    orchestrator: CaseRadarOrchestrator,
    worker_id: str,
    lease_seconds: int,
) -> bool:
    repo.recover_stale_leases()
    run = repo.claim_next(worker_id, lease_seconds)
    if run is None:
        return False

    def cancel_check() -> bool:
        current = repo.get_run(run.id)
        return bool(current and current.cancel_requested_at)

    try:
        result = orchestrator.execute(
            run,
            progress_callback=lambda stage, pct, message: repo.heartbeat(
                run.id,
                worker_id,
                lease_seconds,
                stage=stage,
                progress_percent=pct,
                message=message,
            ),
            cancel_check=cancel_check,
        )
        if cancel_check():
            raise CaseRadarCancelled("Pesquisa cancelada antes da finalização")
        if result.summary.get("no_useful_output"):
            repo.fail(
                run.id,
                worker_id,
                "no_useful_output",
                "A pesquisa terminou sem casos utilizáveis.",
            )
        else:
            repo.complete(
                run.id,
                worker_id,
                partial=result.partial,
                summary=result.summary,
            )
    except CaseRadarCancelled:
        current = repo.get_run(run.id)
        if current is not None and current.status == "running":
            now = repo._now()
            current.status = "cancelled"
            current.stage = "cancelled"
            current.cancel_requested_at = current.cancel_requested_at or now
            current.finished_at = now
            current.lease_expires_at = None
            repo.db.commit()
    except Exception as exc:
        current = repo.get_run(run.id)
        if current is not None and current.status == "running" and current.worker_id == worker_id:
            repo.fail(
                run.id,
                worker_id,
                "case_worker_error",
                f"Falha interna no Case Radar ({type(exc).__name__}). Consulte os logs locais do worker.",
            )
    return True


def main() -> None:
    worker_id = os.getenv("CASE_RADAR_WORKER_ID", "case-worker-1")
    poll_seconds = float(os.getenv("CASE_RADAR_WORKER_POLL_SECONDS", "2"))
    lease_seconds = int(os.getenv("CASE_RADAR_WORKER_LEASE_SECONDS", "180"))
    registry = build_default_registry()

    while True:
        db = SessionLocal()
        try:
            repo = CaseRadarRepository(db)
            orchestrator = CaseRadarOrchestrator(repo, registry)
            worked = run_once(repo, orchestrator, worker_id, lease_seconds)
        finally:
            db.close()
        if not worked:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
