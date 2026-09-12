from datetime import datetime, timezone

from src.case_radar.provenance import EvidenceInput, ProvenanceSource, assess_claim, resolve_provenance


def _dt(year):
    return datetime(year, 1, 1, tzinfo=timezone.utc)


def test_repost_in_2026_pointing_to_2021_resolves_earliest_known_source():
    sources = [
        ProvenanceSource(source_id=1, published_at=_dt(2021), platform="x"),
        ProvenanceSource(source_id=2, published_at=_dt(2026), platform="reddit", links_to_source_ids=(1,)),
    ]
    result = resolve_provenance(sources)
    assert result.earliest_known_source_id == 1
    assert result.likely_original_source_id == 1
    assert result.origin_status == "likely"


def test_single_comment_location_claim_stays_unverified():
    assessment = assess_claim(
        [
            EvidenceInput(
                evidence_id=10,
                stance="supports",
                social_context_item_id=5,
                independence_key="commenter-a",
                evidence_kind="social",
            )
        ]
    )
    assert assessment.status == "unverified"
    assert assessment.supporting_evidence_ids == (10,)


def test_two_independent_sources_corroborate_claim():
    assessment = assess_claim(
        [
            EvidenceInput(evidence_id=1, stance="supports", source_id=1, independence_key="source-a"),
            EvidenceInput(evidence_id=2, stance="supports", source_id=2, independence_key="source-b"),
        ]
    )
    assert assessment.status == "corroborated"
    assert assessment.confidence >= 0.9


def test_independent_support_and_contradiction_is_material_conflict():
    assessment = assess_claim(
        [
            EvidenceInput(evidence_id=1, stance="supports", source_id=1, independence_key="source-a"),
            EvidenceInput(evidence_id=2, stance="contradicts", source_id=2, independence_key="source-b"),
        ]
    )
    assert assessment.status == "contradicted"
    assert assessment.supporting_evidence_ids == (1,)
    assert assessment.contradicting_evidence_ids == (2,)


def test_two_independent_contradictions_mark_claim_contradicted():
    assessment = assess_claim(
        [
            EvidenceInput(evidence_id=1, stance="contradicts", source_id=1, independence_key="a"),
            EvidenceInput(evidence_id=2, stance="contradicts", source_id=2, independence_key="b"),
        ]
    )
    assert assessment.status == "contradicted"
    assert assessment.confidence >= 0.9


def test_author_claim_is_source_claimed_not_confirmed_fact():
    assessment = assess_claim(
        [
            EvidenceInput(
                evidence_id=1,
                stance="supports",
                source_id=1,
                independence_key="author-a",
                author_is_source_author=True,
            )
        ]
    )
    assert assessment.status == "source_claimed"


def test_origin_is_confirmed_only_with_author_confirmation_plus_linkage():
    sources = [
        ProvenanceSource(
            source_id=1,
            published_at=_dt(2020),
            claims_original=True,
            author_confirms_origin=True,
        ),
        ProvenanceSource(source_id=2, published_at=_dt(2021), links_to_source_ids=(1,)),
    ]
    result = resolve_provenance(sources)
    assert result.origin_status == "confirmed"
    assert result.likely_original_source_id == 1


def test_no_sources_returns_unknown_without_inventing_origin():
    result = resolve_provenance([])
    assert result.origin_status == "unknown"
    assert result.earliest_known_source_id is None
    assert result.likely_original_source_id is None
