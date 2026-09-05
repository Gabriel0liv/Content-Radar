from __future__ import annotations

import os
import time

from src.db.session import SessionLocal
from src.repositories.speech_jobs import SpeechJobRepository
from src.services.speech_result_importer import SpeechResultImporter, SpeechResultImportError
from src.services.speech_worker_protocol import JobCancelled, UnsupportedOperationError
from speech_worker.runtime.capabilities import detect_capabilities
from speech_worker.runtime.executor import SpeechExecutor


def run_once(repo: SpeechJobRepository, executor: SpeechExecutor, worker_id: str, lease_seconds: int) -> bool:
    capabilities = detect_capabilities(worker_id)
    repo.upsert_worker_state(worker_id, capabilities.as_dict())
    repo.recover_stale_leases()
    job = repo.claim_next(worker_id, lease_seconds, operations=capabilities.operations)
    if job is None:
        return False

    try:
        def cancel_check() -> bool:
            current = repo.get(job.id)
            return bool(current and current.cancel_requested_at)

        result = executor.execute(
            job,
            progress_callback=lambda stage, pct, msg: repo.heartbeat(
                job.id,
                worker_id,
                lease_seconds,
                stage=stage,
                progress_percent=pct,
                progress_message=msg,
            ),
            cancel_check=cancel_check,
        )
        if cancel_check():
            raise JobCancelled("Job cancelado antes da finalização")

        importer = SpeechResultImporter(repo.db)
        if result.get("kind") == "stt":
            importer.finalize_stt(job, result)
        repo.complete(job.id, worker_id, result)
    except JobCancelled:
        repo.mark_cancelled(job.id, worker_id)
    except SpeechResultImportError as exc:
        repo.fail(job.id, worker_id, "result_import_error", str(exc))
    except UnsupportedOperationError as exc:
        repo.fail(job.id, worker_id, "unsupported_operation", str(exc))
    except Exception as exc:
        repo.fail(job.id, worker_id, "worker_error", str(exc))
    return True


def main() -> None:
    worker_id = os.getenv("SPEECH_WORKER_ID", "local-worker-1")
    poll_seconds = float(os.getenv("SPEECH_WORKER_POLL_SECONDS", "2"))
    lease_seconds = int(os.getenv("SPEECH_WORKER_LEASE_SECONDS", "120"))
    executor = SpeechExecutor()

    while True:
        db = SessionLocal()
        try:
            repo = SpeechJobRepository(db)
            worked = run_once(repo, executor, worker_id, lease_seconds)
        finally:
            db.close()
        if not worked:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
