from datetime import datetime, timezone
from types import SimpleNamespace

from src.case_radar.clustering import compare_sources
from src.case_radar.dossier import build_factual_dossier
from src.case_radar.provenance import ProvenanceSource, resolve_provenance
from src.case_radar.query_generator import generate_queries
from src.case_radar.social_context import classify_social_item, score_social_item
from src.case_radar.types import SocialContextRecord
from src.schemas.case_radar import CaseResearchCreate


def test_offline_pipeline_keeps_social_claim_unverified_and_resolves_earliest_source():
    request = CaseResearchCreate(
        theme="strange forest footage",
        desired_usable_cases=2,
        languages=["en", "pt"],
        platforms=["x", "reddit", "youtube"],
        research_depth="balanced",
        global_result_budget=50,
    )
    queries = generate_queries(request)
    assert queries
    assert {query.intent for query in queries} >= {"core", "source_hunt", "context", "debunk"}

    x_source = SimpleNamespace(
        id=1,
        platform="x",
        external_id="x-2026",
        canonical_url="https://x.com/user/status/2026",
        title_or_caption="Strange forest footage",
        text="A figure appears between the trees at night",
        published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        relation_json={"linked_url": "https://reddit.com/r/mystery/comments/original/post"},
        raw_json={"thumbnail_hash": "same-frame"},
        author_handle="@reposter",
        reference_source_id=None,
    )
    reddit_source = SimpleNamespace(
        id=2,
        platform="reddit",
        external_id="original",
        canonical_url="https://reddit.com/r/mystery/comments/original/post",
        title_or_caption="Strange forest footage",
        text="A figure appears between the trees at night",
        published_at=datetime(2021, 4, 5, tzinfo=timezone.utc),
        relation_json={},
        raw_json={"thumbnail_hash": "same-frame"},
        author_handle="original_poster",
        reference_source_id=None,
    )
    youtube_source = SimpleNamespace(
        id=3,
        platform="youtube",
        external_id="yt-copy",
        canonical_url="https://youtube.com/watch?v=abcdefghijk",
        title_or_caption="Strange forest footage explained",
        text="A figure appears between the trees at night",
        published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        relation_json={"linked_url": "https://reddit.com/r/mystery/comments/original/post"},
        raw_json={"thumbnail_hash": "same-frame"},
        author_handle=None,
        reference_source_id=None,
    )

    assert compare_sources(x_source, reddit_source).action == "merge"
    assert compare_sources(youtube_source, reddit_source).action == "merge"

    comment = SocialContextRecord(
        platform_item_id="c1",
        body="This is from a short film, original source: https://example.com/film",
        engagement={"score": 500},
        external_links=["https://example.com/film"],
    )
    categories = classify_social_item(comment.body)
    assert "debunk" in categories
    assert "link" in categories
    assert score_social_item(comment) > 0

    provenance = resolve_provenance(
        [
            ProvenanceSource(
                source_id=1,
                published_at=x_source.published_at,
                links_to_source_ids=(2,),
            ),
            ProvenanceSource(
                source_id=2,
                published_at=reddit_source.published_at,
            ),
            ProvenanceSource(
                source_id=3,
                published_at=youtube_source.published_at,
                links_to_source_ids=(2,),
            ),
        ]
    )
    assert provenance.earliest_known_source_id == 2
    assert provenance.likely_original_source_id == 2
    assert provenance.origin_status in {"likely", "confirmed"}

    case = SimpleNamespace(
        id=10,
        provisional_title="Strange forest footage",
        normalized_summary="A figure appears between trees in a night recording.",
        status="ready",
        alleged_date=None,
        alleged_location=None,
        earliest_known_date=reddit_source.published_at,
        selected_primary_source_id=2,
        earliest_known_source_id=2,
        likely_original_source_id=2,
        origin_status=provenance.origin_status,
        origin_confidence=provenance.confidence,
        research_confidence=0.78,
        dossier_version=1,
    )
    claim = SimpleNamespace(
        id=20,
        normalized_claim_text=comment.body,
        claim_type="debunk",
        status="unverified",
        confidence=0.35,
    )
    evidence = SimpleNamespace(
        id=30,
        claim_id=20,
        source_id=None,
        social_context_item_id=40,
        transcript_segment_id=None,
        stance="supports",
        note="Pista de comentário ainda não corroborada.",
    )
    social = SimpleNamespace(
        id=40,
        source_id=2,
        body=comment.body,
        author_handle="commenter",
        published_at=None,
        usefulness_score=9.0,
        categories_json=sorted(categories),
        urls_json=comment.external_links,
    )

    dossier = build_factual_dossier(
        case,
        sources=[x_source, reddit_source, youtube_source],
        claims=[claim],
        evidence=[evidence],
        social_context=[social],
        provider_coverage={"x": {"results": 1}, "reddit": {"results": 1}, "youtube": {"results": 1}},
    )

    assert dossier["earliest_known_source"]["id"] == 2
    assert dossier["likely_original_source"]["id"] == 2
    assert dossier["verified_context"] == []
    assert dossier["alternative_explanations"][0]["status"] == "unverified"
    assert dossier["alternative_explanations"][0]["evidence_ids"] == [30]
