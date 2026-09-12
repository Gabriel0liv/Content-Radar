from types import SimpleNamespace

import pytest

from src.case_radar.orchestrator import CaseRadarCancelled, CaseRadarOrchestrator, OrchestratorResult


class FakeDb:
    def __init__(self):
        self.commits = 0
        self.added = []

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1


class FakeRepo:
    def __init__(self):
        self.db = FakeDb()
        self.sources = []

    def list_sources(self, run_id):
        return list(self.sources)


class FakeRegistry:
    pass


class RecordingOrchestrator(CaseRadarOrchestrator):
    def __init__(self, repo, registry, *, provider_errors=None, source_count=3, case_count=2):
        super().__init__(repo, registry)
        self.calls = []
        self.provider_errors = provider_errors or []
        self.source_count = source_count
        self.case_count = case_count
        self.persisted_queries = [SimpleNamespace(id=1)]

    def _persist_queries(self, run_id, request):
        self.calls.append("queries")
        return self.persisted_queries

    def _discover(self, run_id, request, queries, cancel_check):
        self.calls.append("discover")
        sources = [SimpleNamespace(id=index + 1) for index in range(self.source_count)]
        self.repo.sources = sources
        coverage = {
            "youtube": {
                "queries": 1,
                "results": len(sources),
                "methods": ["youtube-official"],
                "errors": list(self.provider_errors),
            }
        }
        return sources, coverage, list(self.provider_errors)

    def _enrich_sources(self, sources, cancel_check):
        self.calls.append("enrich")

    def _collect_social_context(self, sources, request, cancel_check):
        self.calls.append("social")

    def _cluster(self, run_id, sources):
        self.calls.append("cluster")
        return [SimpleNamespace(id=index + 1, status="ready") for index in range(self.case_count)]

    def _research_cases(self, run_id, cases, provider_coverage):
        self.calls.append("research")
        return cases


def _run(target=2):
    return SimpleNamespace(
        id=1,
        request_json={
            "theme": "strange forest videos",
            "desired_usable_cases": target,
            "languages": ["en"],
            "platforms": ["youtube"],
            "global_result_budget": 20,
        },
        provider_coverage_json={},
        discovered_candidates=0,
        clustered_cases=0,
        usable_cases=0,
        rejected_cases=0,
        errors_json=[],
    )


def test_orchestrator_runs_all_stages_and_returns_completed_result():
    repo = FakeRepo()
    orchestrator = RecordingOrchestrator(repo, FakeRegistry())
    progress = []

    result = orchestrator.execute(
        _run(target=2),
        progress_callback=lambda stage, pct, message: progress.append(stage),
    )

    assert isinstance(result, OrchestratorResult)
    assert result.partial is False
    assert orchestrator.calls == ["queries", "discover", "enrich", "social", "cluster", "research"]
    assert progress == [
        "generating_queries",
        "discovering",
        "enriching_sources",
        "collecting_social_context",
        "clustering_cases",
        "researching_cases",
        "finalizing",
    ]
    assert result.summary["usable_cases"] == 2


def test_orchestrator_marks_partial_when_target_missed_but_has_useful_output():
    repo = FakeRepo()
    orchestrator = RecordingOrchestrator(repo, FakeRegistry(), case_count=2)
    result = orchestrator.execute(_run(target=5))
    assert result.partial is True
    assert result.summary["usable_cases"] == 2
    assert result.summary["desired_usable_cases"] == 5


def test_orchestrator_marks_partial_when_provider_errors_exist():
    repo = FakeRepo()
    orchestrator = RecordingOrchestrator(
        repo,
        FakeRegistry(),
        provider_errors=[{"code": "provider_unavailable", "message": "fallback used"}],
        case_count=2,
    )
    result = orchestrator.execute(_run(target=2))
    assert result.partial is True
    assert result.summary["provider_errors"]


def test_orchestrator_cancels_between_expensive_stages():
    repo = FakeRepo()
    orchestrator = RecordingOrchestrator(repo, FakeRegistry())
    checks = {"count": 0}

    def cancel_check():
        checks["count"] += 1
        return checks["count"] >= 3

    with pytest.raises(CaseRadarCancelled):
        orchestrator.execute(_run(), cancel_check=cancel_check)
    assert orchestrator.calls[:2] == ["queries", "discover"]


def test_query_persistence_is_delegated_before_discovery_on_retry():
    repo = FakeRepo()
    orchestrator = RecordingOrchestrator(repo, FakeRegistry())
    run = _run()
    first = orchestrator.execute(run)
    first_calls = list(orchestrator.calls)
    orchestrator.calls.clear()
    second = orchestrator.execute(run)
    assert first.summary["usable_cases"] == second.summary["usable_cases"]
    assert first_calls == orchestrator.calls
