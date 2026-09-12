from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from src.case_radar.types import Candidate
from src.models.case_radar import CaseResearchRun
from src.repositories.case_radar import CaseRadarRepository


class ScalarOneOrNoneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ScalarsResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return list(self.values)


class FakeDb:
    def __init__(self, execute_result=None):
        self.execute_result = execute_result
        self.executed = []
        self.added = []
        self.commits = 0
        self.rollbacks = 0

    def execute(self, statement):
        self.executed.append(statement)
        if callable(self.execute_result):
            return self.execute_result(statement)
        return self.execute_result

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, value):
        return None

    def get(self, model, key):
        return None


def _candidate(url: str = "https://example.com/case") -> Candidate:
    return Candidate(
        platform="web",
        canonical_url=url,
        title_or_caption="Strange lights recorded above the forest",
        text="Witness footage of unusual lights.",
        discovery_query="strange lights",
        discovery_method="web_search",
        source_confidence=0.5,
    )


def test_claim_next_uses_skip_locked_and_assigns_lease():
    run = CaseResearchRun(request_json={"theme": "floresta"})
    run.id = 7
    run.status = "queued"
    run.stage = "queued"
    run.created_at = datetime.now(timezone.utc)
    db = FakeDb(ScalarOneOrNoneResult(run))
    repo = CaseRadarRepository(db)

    claimed = repo.claim_next("case-worker-1", 180)

    compiled = str(db.executed[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE SKIP LOCKED" in compiled
    assert claimed is run
    assert run.status == "running"
    assert run.stage == "generating_queries"
    assert run.worker_id == "case-worker-1"
    assert run.lease_expires_at is not None
    assert db.commits == 1


def test_claim_next_rolls_back_when_queue_is_empty():
    db = FakeDb(ScalarOneOrNoneResult(None))
    repo = CaseRadarRepository(db)
    assert repo.claim_next("case-worker-1", 180) is None
    assert db.rollbacks == 1


def test_heartbeat_extends_owned_run_and_updates_progress():
    run = SimpleNamespace(
        id=4,
        status="running",
        worker_id="worker-a",
        heartbeat_at=None,
        lease_expires_at=None,
        stage="discovering",
        progress_percent=10,
        progress_message=None,
    )
    db = FakeDb()
    repo = CaseRadarRepository(db)
    repo.get_run = lambda run_id: run

    result = repo.heartbeat(
        4,
        "worker-a",
        120,
        stage="collecting_social_context",
        progress_percent=55,
        message="Coletando comentários",
    )

    assert result.stage == "collecting_social_context"
    assert result.progress_percent == 55
    assert result.progress_message == "Coletando comentários"
    assert result.heartbeat_at is not None
    assert result.lease_expires_at > result.heartbeat_at


def test_cancel_queued_run_finishes_immediately():
    run = SimpleNamespace(
        status="queued",
        stage="queued",
        progress_message=None,
        cancel_requested_at=None,
        finished_at=None,
        lease_expires_at=None,
    )
    db = FakeDb()
    repo = CaseRadarRepository(db)
    repo.get_run = lambda run_id: run

    result = repo.request_cancel(9)

    assert result.status == "cancelled"
    assert result.stage == "cancelled"
    assert result.cancel_requested_at is not None
    assert result.finished_at is not None


def test_cancel_running_run_sets_request_without_stealing_worker():
    run = SimpleNamespace(
        status="running",
        stage="discovering",
        worker_id="worker-a",
        cancel_requested_at=None,
    )
    db = FakeDb()
    repo = CaseRadarRepository(db)
    repo.get_run = lambda run_id: run

    repo.request_cancel(5)

    assert run.status == "running"
    assert run.worker_id == "worker-a"
    assert run.cancel_requested_at is not None


def test_recover_stale_lease_requeues_non_cancelled_run():
    now = datetime.now(timezone.utc)
    run = SimpleNamespace(
        status="running",
        stage="researching_cases",
        lease_expires_at=now - timedelta(seconds=1),
        cancel_requested_at=None,
        worker_id="dead-worker",
        heartbeat_at=now - timedelta(minutes=5),
        finished_at=None,
    )
    db = FakeDb(ScalarsResult([run]))
    repo = CaseRadarRepository(db)

    count = repo.recover_stale_leases(now)

    assert count == 1
    assert run.status == "queued"
    assert run.stage == "researching_cases"
    assert run.worker_id is None
    assert run.lease_expires_at is None
    assert run.heartbeat_at is None


def test_recover_stale_lease_finishes_cancelled_run():
    now = datetime.now(timezone.utc)
    run = SimpleNamespace(
        status="running",
        stage="discovering",
        lease_expires_at=now - timedelta(seconds=1),
        cancel_requested_at=now - timedelta(seconds=30),
        worker_id="dead-worker",
        heartbeat_at=now - timedelta(minutes=5),
        finished_at=None,
    )
    db = FakeDb(ScalarsResult([run]))
    repo = CaseRadarRepository(db)

    repo.recover_stale_leases(now)

    assert run.status == "cancelled"
    assert run.stage == "cancelled"
    assert run.finished_at == now


def test_upsert_source_keeps_existing_seed_query_when_rediscovered_by_context():
    source = SimpleNamespace(
        query_id=10,
        platform="web",
        external_id=None,
        canonical_url="https://example.com/case",
    )
    queries = {
        10: SimpleNamespace(id=10, intent="core"),
        20: SimpleNamespace(id=20, intent="context"),
    }
    db = FakeDb(ScalarOneOrNoneResult(source))
    db.get = lambda model, key: queries.get(key)
    repo = CaseRadarRepository(db)

    result = repo.upsert_source(_candidate(), run_id=1, query_id=20)

    assert result.query_id == 10


def test_upsert_source_promotes_auxiliary_query_to_seed_query_when_rediscovered_by_core():
    source = SimpleNamespace(
        query_id=20,
        platform="web",
        external_id=None,
        canonical_url="https://example.com/case",
    )
    queries = {
        10: SimpleNamespace(id=10, intent="core"),
        20: SimpleNamespace(id=20, intent="context"),
    }
    db = FakeDb(ScalarOneOrNoneResult(source))
    db.get = lambda model, key: queries.get(key)
    repo = CaseRadarRepository(db)

    result = repo.upsert_source(_candidate(), run_id=1, query_id=10)

    assert result.query_id == 10
