from datetime import datetime, timezone
from types import SimpleNamespace

import json
import pytest

from src.case_radar.dossier import DossierValidationError, build_dossier, build_factual_dossier


def _case(**overrides):
    data = {
        "id": 1,
        "provisional_title": "Caso da floresta",
        "normalized_summary": "Um vídeo mostra uma figura ao fundo de uma trilha.",
        "status": "ready",
        "alleged_date": None,
        "alleged_location": "Canadá",
        "earliest_known_date": None,
        "selected_primary_source_id": 10,
        "earliest_known_source_id": 10,
        "likely_original_source_id": 10,
        "origin_status": "likely",
        "origin_confidence": 0.75,
        "research_confidence": 0.8,
        "dossier_version": 1,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _source(source_id=10):
    return SimpleNamespace(
        id=source_id,
        platform="x",
        canonical_url=f"https://x.com/u/status/{source_id}",
        title_or_caption="Vídeo da floresta",
        author_handle="@u",
        published_at=None,
        reference_source_id=None,
    )


def _claim(claim_id, status, claim_type="context"):
    return SimpleNamespace(
        id=claim_id,
        normalized_claim_text=f"claim {claim_id}",
        status=status,
        confidence=0.8,
        claim_type=claim_type,
    )


def _evidence(evidence_id, claim_id, stance="supports"):
    return SimpleNamespace(
        id=evidence_id,
        claim_id=claim_id,
        source_id=10,
        social_context_item_id=None,
        transcript_segment_id=None,
        stance=stance,
        note=None,
    )


def test_dossier_separates_verified_unverified_contradicted_and_alternatives():
    dossier = build_factual_dossier(
        _case(),
        sources=[_source()],
        claims=[
            _claim(1, "corroborated"),
            _claim(2, "unverified"),
            _claim(3, "contradicted"),
            _claim(4, "source_claimed", "debunk"),
        ],
        evidence=[
            _evidence(101, 1),
            _evidence(102, 2),
            _evidence(103, 3, "contradicts"),
            _evidence(104, 4),
        ],
        provider_coverage={"x": {"status": "ok"}},
    )

    assert [item["id"] for item in dossier["verified_context"]] == [1]
    assert [item["id"] for item in dossier["unverified_claims"]] == [2]
    assert [item["id"] for item in dossier["contradictions"]] == [3]
    assert [item["id"] for item in dossier["alternative_explanations"]] == [4]
    assert dossier["primary_source"]["id"] == 10
    assert dossier["provider_coverage"]["x"]["status"] == "ok"


def test_every_material_claim_requires_evidence_ids():
    with pytest.raises(DossierValidationError):
        build_factual_dossier(
            _case(),
            sources=[_source()],
            claims=[_claim(1, "corroborated")],
            evidence=[],
        )


def test_transcript_timestamps_are_preserved_in_dossier():
    segment = SimpleNamespace(
        id=90,
        transcript_id=3,
        start_time=12.5,
        end_time=16.0,
        speaker="SPEAKER_00",
        text="olha aquilo",
    )
    dossier = build_factual_dossier(
        _case(),
        sources=[_source()],
        claims=[],
        evidence=[],
        transcript_segments=[segment],
    )
    assert dossier["transcript_segments"][0]["start_time"] == 12.5
    assert dossier["transcript_segments"][0]["text"] == "olha aquilo"


def test_ai_summarizer_cannot_replace_sources_or_claim_sections():
    def malicious_summary(factual):
        return {
            "summary": "resumo melhor",
            "sources": [{"id": 999, "url": "https://fake.invalid"}],
            "verified_context": [{"id": 999, "evidence_ids": [999]}],
        }

    dossier = build_dossier(
        _case(),
        sources=[_source()],
        claims=[_claim(1, "corroborated")],
        evidence=[_evidence(101, 1)],
        summarizer=malicious_summary,
    )
    assert dossier["summary"] == "resumo melhor"
    assert dossier["sources"][0]["id"] == 10
    assert dossier["verified_context"][0]["id"] == 1


def test_summarizer_failure_falls_back_to_factual_dossier():
    def broken(_):
        raise RuntimeError("LLM down")

    dossier = build_dossier(
        _case(),
        sources=[_source()],
        claims=[],
        evidence=[],
        summarizer=broken,
    )
    assert dossier["title"] == "Caso da floresta"


def test_dossier_is_json_serializable_when_dates_are_datetimes():
    published = datetime(2025, 8, 29, 21, 30, tzinfo=timezone.utc)
    source = _source()
    source.published_at = published
    social = SimpleNamespace(
        id=55,
        source_id=source.id,
        body="comentário",
        author_handle="@viewer",
        published_at=published,
        usefulness_score=5.0,
        categories_json=["context"],
        urls_json=[],
    )

    dossier = build_factual_dossier(
        _case(earliest_known_date=published, alleged_date=published),
        sources=[source],
        claims=[],
        evidence=[],
        social_context=[social],
        provider_coverage={"web": {"checked_at": published}},
    )

    encoded = json.dumps(dossier)
    assert "2025-08-29T21:30:00+00:00" in encoded
    assert dossier["earliest_known_date"] == published.isoformat()
    assert dossier["sources"][0]["published_at"] == published.isoformat()
    assert dossier["useful_social_context"][0]["published_at"] == published.isoformat()
