from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.case_radar.types import Candidate, ProviderCapabilities
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
