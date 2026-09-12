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
        self.claims = []
        self.evidence = []
        self.case_links = []

    def list_sources(self, run_id):
        return list(self.sources)

    def upsert_source(self, candidate, run_id, query_id):
        for source in self.sources:
            if source.canonical_url == candidate.canonical_url:
                return source
        source = SimpleNamespace(
            id=len(self.sources) + 1,
            run_id=run_id,
            query_id=query_id,
            platform=candidate.platform,
            canonical_url=candidate.canonical_url,
            external_id=candidate.external_id,
            discovery_method=candidate.discovery_method,
            source_confidence=candidate.source_confidence,
            title_or_caption=candidate.title_or_caption,
            text=candidate.text,
            published_at=candidate.published_at,
            author_handle=candidate.author_handle,
            author_display_name=candidate.author_display_name,
            media_type=candidate.media_type,
            thumbnail_url=candidate.thumbnail_url,
            duration_seconds=candidate.duration_seconds,
            language=candidate.language,
            engagement_json=candidate.engagement,
            hashtags_json=candidate.hashtags,
            relation_json=candidate.relation,
            raw_json=candidate.raw_json,
        )
        self.sources.append(source)
        return source

    def link_case_source(self, **payload):
        self.case_links.append(payload)
        return SimpleNamespace(id=len(self.case_links), **payload)

    def upsert_claim(self, **payload):
        claim = SimpleNamespace(id=len(self.claims) + 1, **payload)
        self.claims.append(claim)
        return claim

    def link_evidence(self, **payload):
        self.evidence.append(payload)
        return SimpleNamespace(id=len(self.evidence), **payload)


class FakeRegistry:
    def methods_for(self, platform):
        return []

    def get(self, platform, method):
        return None


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


def test_social_debunk_becomes_unverified_claim_with_social_evidence():
    repo = FakeRepo()
    orchestrator = CaseRadarOrchestrator(repo, FakeRegistry())
    case = SimpleNamespace(id=7)
    comment = SimpleNamespace(
        id=12,
        source_id=3,
        body="Isso é de um curta-metragem, a cena original está aqui.",
        categories_json=["debunk", "link"],
        author_reply=False,
        usefulness_score=8.0,
    )

    orchestrator._materialize_social_claims(case, [comment])

    assert len(repo.claims) == 1
    assert repo.claims[0].claim_type == "debunk"
    assert repo.claims[0].status == "unverified"
    assert repo.evidence == [
        {
            "claim_id": 1,
            "stance": "supports",
            "social_context_item_id": 12,
            "source_id": 3,
            "note": "Pista extraída de comentário/resposta; não tratada como fato sem corroboração independente.",
        }
    ]


def test_author_response_is_source_claimed_but_not_corroborated():
    repo = FakeRepo()
    orchestrator = CaseRadarOrchestrator(repo, FakeRegistry())
    case = SimpleNamespace(id=7)
    comment = SimpleNamespace(
        id=14,
        source_id=3,
        body="Eu gravei isso perto de Coimbra em 2021.",
        categories_json=["author_response", "context"],
        author_reply=True,
        usefulness_score=12.0,
    )

    orchestrator._materialize_social_claims(case, [comment])

    assert repo.claims[0].claim_type == "context"
    assert repo.claims[0].status == "source_claimed"
    assert repo.claims[0].confidence < 0.7


def test_comment_link_to_existing_source_becomes_provenance_edge():
    repo = FakeRepo()
    orchestrator = CaseRadarOrchestrator(repo, FakeRegistry())
    sources = [
        SimpleNamespace(id=1, canonical_url="https://x.com/user/status/100"),
        SimpleNamespace(id=2, canonical_url="https://reddit.com/r/test/comments/abc/post"),
    ]
    social = [
        SimpleNamespace(
            source_id=1,
            urls_json=["https://www.reddit.com/r/test/comments/abc/post/?utm_source=share"],
        )
    ]

    targets = orchestrator._social_link_targets(sources, social)

    assert targets[1] == {2}


def test_comment_link_to_new_url_becomes_auxiliary_source_of_same_case():
    repo = FakeRepo()
    origin = SimpleNamespace(
        id=1,
        run_id=9,
        query_id=4,
        platform="reddit",
        canonical_url="https://reddit.com/r/test/comments/abc/post",
    )
    repo.sources = [origin]
    orchestrator = CaseRadarOrchestrator(repo, FakeRegistry())
    case = SimpleNamespace(id=22, run_id=9)
    social = [
        SimpleNamespace(
            id=31,
            source_id=1,
            urls_json=["https://x.com/original/status/123?utm_source=share"],
            categories_json=["origin", "link"],
            body="Original source: https://x.com/original/status/123",
        )
    ]

    promoted = orchestrator._promote_social_links(case, repo.sources, social)

    assert len(promoted) == 1
    assert promoted[0].platform == "x"
    assert promoted[0].canonical_url == "https://x.com/original/status/123"
    assert promoted[0].discovery_method == "social_link"
    assert repo.case_links == [
        {
            "case_id": 22,
            "source_id": promoted[0].id,
            "role": "original_candidate",
            "provenance_confidence": 0.45,
            "reason": "URL citada em comentário/resposta classificada como pista de origem.",
            "evidence_json": {"social_context_item_id": 31, "source_id": 1},
        }
    ]
