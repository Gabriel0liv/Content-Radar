from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.case_radar.types import Candidate, ProviderCapabilities
from src.models.case_radar import (
    CaseClaim,
    CaseEvidence,
    CaseResearchQuery,
    CaseResearchRun,
    CaseSource,
    MediaFingerprint,
    ResearchCase,
    ResearchSource,
    SocialContextItem,
)
from src.schemas.case_radar import CaseResearchCreate


def test_provider_capabilities_accepts_declared_contract():
    capabilities = ProviderCapabilities(
        search_supported=True,
        source_fetch_supported=True,
        comments_supported=False,
        replies_supported=False,
        quote_posts_supported=False,
        media_metadata_supported=True,
        historical_search_supported=True,
        authenticated=False,
        official_api=True,
        cost_class="metered",
    )
    assert capabilities.cost_class == "metered"


def test_candidate_accepts_canonical_shape():
    candidate = Candidate(
        platform="youtube",
        external_id="abc123",
        canonical_url="https://www.youtube.com/watch?v=abc123",
        author_handle="@canal",
        author_display_name="Canal",
        title_or_caption="Vídeo estranho",
        text="descrição",
        published_at=datetime.now(timezone.utc),
        media_type="video",
        thumbnail_url=None,
        duration_seconds=30.5,
        language="pt",
        engagement={"views": 100, "likes": 5},
        hashtags=["misterio"],
        relation=None,
        discovery_query="vídeo estranho floresta",
        discovery_method="official_api",
        raw_json={"id": "abc123"},
        source_confidence=0.9,
    )
    assert candidate.platform == "youtube"
    assert candidate.engagement["views"] == 100


@pytest.mark.parametrize("theme", ["", "   ", "\n\t"])
def test_research_request_rejects_empty_theme(theme):
    with pytest.raises(ValidationError):
        CaseResearchCreate(theme=theme)


@pytest.mark.parametrize("target", [0, 51])
def test_research_request_rejects_target_outside_1_to_50(target):
    with pytest.raises(ValidationError):
        CaseResearchCreate(theme="casos estranhos", desired_usable_cases=target)


@pytest.mark.parametrize("budget", [0, 5001])
def test_research_request_rejects_invalid_global_budget(budget):
    with pytest.raises(ValidationError):
        CaseResearchCreate(theme="casos estranhos", global_result_budget=budget)


def test_research_request_rejects_inverted_date_range():
    with pytest.raises(ValidationError):
        CaseResearchCreate(
            theme="casos estranhos",
            date_from=date(2026, 9, 12),
            date_to=date(2026, 9, 11),
        )


def test_research_request_normalizes_theme_languages_and_terms():
    request = CaseResearchCreate(
        theme="  vídeos   estranhos na floresta  ",
        languages=["PT", "en", "pt"],
        include_terms=["  trail camera  ", "trail camera"],
        exclude_terms=[" ARG ", "ARG"],
        provider_budgets={"youtube": 100, "reddit": 50},
    )
    assert request.theme == "vídeos estranhos na floresta"
    assert request.languages == ["pt", "en"]
    assert request.include_terms == ["trail camera"]
    assert request.exclude_terms == ["ARG"]


def test_research_request_rejects_invalid_provider_budget():
    with pytest.raises(ValidationError):
        CaseResearchCreate(
            theme="casos estranhos",
            provider_budgets={"youtube": -1},
        )


def test_case_research_run_exposes_queue_and_lease_fields():
    columns = CaseResearchRun.__table__.columns
    for name in (
        "status",
        "stage",
        "progress_percent",
        "request_json",
        "provider_coverage_json",
        "worker_id",
        "lease_expires_at",
        "heartbeat_at",
        "cancel_requested_at",
        "errors_json",
    ):
        assert name in columns


def test_case_radar_models_register_expected_tables():
    assert CaseResearchQuery.__tablename__ == "case_research_queries"
    assert ResearchSource.__tablename__ == "research_sources"
    assert ResearchCase.__tablename__ == "research_cases"
    assert CaseSource.__tablename__ == "case_sources"
    assert SocialContextItem.__tablename__ == "social_context_items"
    assert CaseClaim.__tablename__ == "case_claims"
    assert CaseEvidence.__tablename__ == "case_evidence"
    assert MediaFingerprint.__tablename__ == "media_fingerprints"


def test_research_source_links_existing_content_and_reference_models():
    columns = ResearchSource.__table__.columns
    assert "content_item_id" in columns
    assert "reference_source_id" in columns


def test_case_evidence_requires_at_least_one_evidence_target():
    constraints = {
        constraint.name: str(constraint.sqltext)
        for constraint in CaseEvidence.__table__.constraints
        if getattr(constraint, "name", None)
    }
    expression = constraints["check_case_evidence_has_target"]
    assert "source_id IS NOT NULL" in expression
    assert "social_context_item_id IS NOT NULL" in expression
    assert "transcript_segment_id IS NOT NULL" in expression


def test_case_source_is_unique_per_case_and_source():
    names = {constraint.name for constraint in CaseSource.__table__.constraints}
    assert "uq_case_sources_case_source" in names


def test_social_context_preserves_parent_relationship():
    assert "parent_social_context_id" in SocialContextItem.__table__.columns
