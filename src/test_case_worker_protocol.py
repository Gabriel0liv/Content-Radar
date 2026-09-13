from types import SimpleNamespace

from case_worker.worker import run_once
from src.case_radar.orchestrator import CaseRadarCancelled, OrchestratorResult


class FakeDb:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FakeRepo:
    def __init__(self, run):
        self.run = run
        self.db = FakeDb()
        self.recovered = 0
        self.heartbeats = []
        self.completed = None
        self.failed = None

    @staticmethod
    def _now():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

    def recover_stale_leases(self):
        self.recovered += 1

    def claim_next(self, worker_id, lease_seconds):
        if self.run is None:
            return None
        self.run.worker_id = worker_id
        self.run.status = "running"
        return self.run

    def get_run(self, run_id):
        return self.run

    def heartbeat(self, run_id, worker_id, lease_seconds, *, stage, progress_percent, message):
        self.heartbeats.append((stage, progress_percent, message))
        return self.run

    def complete(self, run_id, worker_id, *, partial, summary):
        self.completed = {"partial": partial, "summary": summary}
        self.run.status = "partially_completed" if partial else "completed"
        return self.run

    def fail(self, run_id, worker_id, error_code, error_message):
        self.failed = (error_code, error_message)
        self.run.status = "failed"
        return self.run


class FakeOrchestrator:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def execute(self, run, *, progress_callback, cancel_check):
        progress_callback("discovering", 20, "descobrindo")
        if self.error:
            raise self.error
        return self.result


def _run():
    return SimpleNamespace(
        id=1,
        status="queued",
        stage="queued",
        worker_id=None,
        cancel_requested_at=None,
        finished_at=None,
        lease_expires_at=None,
    )


def test_run_once_returns_false_when_queue_is_empty():
    repo = FakeRepo(None)
    worked = run_once(repo, FakeOrchestrator(), "worker", 180)
    assert worked is False
    assert repo.recovered == 1


def test_run_once_completes_successful_run():
    repo = FakeRepo(_run())
    orchestrator = FakeOrchestrator(
        result=OrchestratorResult(partial=False, summary={"usable_cases": 3})
    )
    assert run_once(repo, orchestrator, "worker", 180) is True
    assert repo.completed == {"partial": False, "summary": {"usable_cases": 3}}
    assert repo.heartbeats[0][0] == "discovering"


def test_run_once_marks_partial_completion():
    repo = FakeRepo(_run())
    orchestrator = FakeOrchestrator(
        result=OrchestratorResult(partial=True, summary={"usable_cases": 1})
    )
    run_once(repo, orchestrator, "worker", 180)
    assert repo.completed["partial"] is True


def test_run_once_fails_when_orchestrator_has_no_useful_output():
    repo = FakeRepo(_run())
    orchestrator = FakeOrchestrator(
        result=OrchestratorResult(partial=False, summary={"no_useful_output": True})
    )
    run_once(repo, orchestrator, "worker", 180)
    assert repo.failed[0] == "no_useful_output"


def test_run_once_turns_cancellation_into_cancelled_state():
    run = _run()
    repo = FakeRepo(run)
    orchestrator = FakeOrchestrator(error=CaseRadarCancelled("cancel"))
    run_once(repo, orchestrator, "worker", 180)
    assert run.status == "cancelled"
    assert run.stage == "cancelled"
    assert run.finished_at is not None


def test_run_once_does_not_persist_raw_unexpected_exception_message():
    repo = FakeRepo(_run())
    orchestrator = FakeOrchestrator(error=RuntimeError("token=super-secret"))
    run_once(repo, orchestrator, "worker", 180)
    assert repo.failed[0] == "case_worker_error"
    assert "super-secret" not in repo.failed[1]
