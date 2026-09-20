from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class DossierClaim:
    id: int
    text: str
    status: str
    confidence: float
    evidence_ids: tuple[int, ...]
    supporting_evidence_ids: tuple[int, ...]
    contradicting_evidence_ids: tuple[int, ...]
    claim_type: str | None = None


class DossierValidationError(ValueError):
    pass


def _get(value: Any, name: str, default=None):
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    return value


def _source_payload(source: Any) -> dict[str, Any]:
    return {
        "id": _get(source, "id"),
        "platform": _get(source, "platform"),
        "url": _get(source, "canonical_url"),
        "title": _get(source, "title_or_caption"),
        "author_handle": _get(source, "author_handle"),
        "published_at": _get(source, "published_at"),
        "reference_source_id": _get(source, "reference_source_id"),
    }


def _evidence_payload(evidence: Any) -> dict[str, Any]:
    return {
        "id": _get(evidence, "id"),
        "claim_id": _get(evidence, "claim_id"),
        "source_id": _get(evidence, "source_id"),
        "social_context_item_id": _get(evidence, "social_context_item_id"),
        "transcript_segment_id": _get(evidence, "transcript_segment_id"),
        "stance": _get(evidence, "stance"),
        "note": _get(evidence, "note"),
    }


def _build_claim_payload(claim: Any, evidence: list[Any]) -> DossierClaim:
    claim_id = int(_get(claim, "id"))
    claim_evidence = [item for item in evidence if _get(item, "claim_id") == claim_id]
    supporting = tuple(
        int(_get(item, "id"))
        for item in claim_evidence
        if _get(item, "stance") == "supports"
    )
    contradicting = tuple(
        int(_get(item, "id"))
        for item in claim_evidence
        if _get(item, "stance") == "contradicts"
    )
    context = tuple(
        int(_get(item, "id"))
        for item in claim_evidence
        if _get(item, "stance") == "context_only"
    )
    all_evidence = tuple(dict.fromkeys((*supporting, *contradicting, *context)))
    return DossierClaim(
        id=claim_id,
        text=str(_get(claim, "normalized_claim_text", "")),
        status=str(_get(claim, "status", "unverified")),
        confidence=float(_get(claim, "confidence", 0.0) or 0.0),
        evidence_ids=all_evidence,
        supporting_evidence_ids=supporting,
        contradicting_evidence_ids=contradicting,
        claim_type=_get(claim, "claim_type"),
    )


def _serialize_claim(claim: DossierClaim) -> dict[str, Any]:
    return {
        "id": claim.id,
        "text": claim.text,
        "claim_type": claim.claim_type,
        "status": claim.status,
        "confidence": claim.confidence,
        "evidence_ids": list(claim.evidence_ids),
        "supporting_evidence_ids": list(claim.supporting_evidence_ids),
        "contradicting_evidence_ids": list(claim.contradicting_evidence_ids),
    }


def validate_dossier_evidence(dossier: dict[str, Any], valid_evidence_ids: set[int]) -> None:
    sections = (
        "verified_context",
        "unverified_claims",
        "contradictions",
        "alternative_explanations",
    )
    for section in sections:
        for claim in dossier.get(section, []) or []:
            ids = claim.get("evidence_ids") or []
            if not ids:
                raise DossierValidationError(
                    f"Claim material sem evidence_ids na seção {section}: {claim.get('id')}"
                )
            unknown = {int(value) for value in ids} - valid_evidence_ids
            if unknown:
                raise DossierValidationError(
                    f"Claim referencia evidence IDs inexistentes: {sorted(unknown)}"
                )


def build_factual_dossier(
    case: Any,
    *,
    sources: Iterable[Any],
    claims: Iterable[Any],
    evidence: Iterable[Any],
    social_context: Iterable[Any] = (),
    transcript_segments: Iterable[Any] = (),
    provider_coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_list = list(sources)
    claim_list = list(claims)
    evidence_list = list(evidence)
    social_list = list(social_context)
    transcript_list = list(transcript_segments)
    source_by_id = {int(_get(source, "id")): source for source in source_list if _get(source, "id") is not None}
    valid_evidence_ids = {int(_get(item, "id")) for item in evidence_list if _get(item, "id") is not None}

    dossier_claims = [_build_claim_payload(claim, evidence_list) for claim in claim_list]
    verified: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    contradictions: list[dict[str, Any]] = []
    alternatives: list[dict[str, Any]] = []

    for claim in dossier_claims:
        serialized = _serialize_claim(claim)
        if claim.claim_type in {"debunk", "alternative_explanation", "technical_explanation"}:
            alternatives.append(serialized)
        elif claim.status == "corroborated":
            verified.append(serialized)
        elif claim.status == "contradicted":
            contradictions.append(serialized)
        else:
            unverified.append(serialized)

    primary_id = _get(case, "selected_primary_source_id")
    earliest_id = _get(case, "earliest_known_source_id")
    likely_id = _get(case, "likely_original_source_id")

    useful_social = []
    for item in sorted(
        social_list,
        key=lambda value: -float(_get(value, "usefulness_score", 0.0) or 0.0),
    ):
        useful_social.append(
            {
                "id": _get(item, "id"),
                "source_id": _get(item, "source_id"),
                "body": _get(item, "body"),
                "author_handle": _get(item, "author_handle"),
                "published_at": _get(item, "published_at"),
                "usefulness_score": float(_get(item, "usefulness_score", 0.0) or 0.0),
                "categories": list(_get(item, "categories_json", []) or []),
                "urls": list(_get(item, "urls_json", []) or []),
            }
        )

    transcript_payload = [
        {
            "id": _get(segment, "id"),
            "transcript_id": _get(segment, "transcript_id"),
            "start_time": _get(segment, "start_time"),
            "end_time": _get(segment, "end_time"),
            "speaker": _get(segment, "speaker"),
            "text": _get(segment, "text"),
        }
        for segment in transcript_list
    ]

    dossier = {
        "case_id": _get(case, "id"),
        "title": _get(case, "provisional_title"),
        "summary": _get(case, "normalized_summary"),
        "what_happens": _get(case, "normalized_summary"),
        "status": _get(case, "status"),
        "alleged_date": _get(case, "alleged_date"),
        "alleged_location": _get(case, "alleged_location"),
        "earliest_known_date": _get(case, "earliest_known_date"),
        "primary_source": _source_payload(source_by_id[primary_id]) if primary_id in source_by_id else None,
        "earliest_known_source": _source_payload(source_by_id[earliest_id]) if earliest_id in source_by_id else None,
        "likely_original_source": _source_payload(source_by_id[likely_id]) if likely_id in source_by_id else None,
        "sources": [_source_payload(source) for source in source_list],
        "verified_context": verified,
        "unverified_claims": unverified,
        "contradictions": contradictions,
        "alternative_explanations": alternatives,
        "useful_social_context": useful_social,
        "transcript_segments": transcript_payload,
        "evidence": [_evidence_payload(item) for item in evidence_list],
        "origin_status": _get(case, "origin_status", "unknown"),
        "provenance_confidence": float(_get(case, "origin_confidence", 0.0) or 0.0),
        "research_confidence": float(_get(case, "research_confidence", 0.0) or 0.0),
        "provider_coverage": provider_coverage or {},
        "dossier_version": int(_get(case, "dossier_version", 1) or 1),
    }
    dossier = _json_safe(dossier)
    validate_dossier_evidence(dossier, valid_evidence_ids)
    return dossier


def build_dossier(
    case: Any,
    *,
    sources: Iterable[Any],
    claims: Iterable[Any],
    evidence: Iterable[Any],
    social_context: Iterable[Any] = (),
    transcript_segments: Iterable[Any] = (),
    provider_coverage: dict[str, Any] | None = None,
    summarizer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    factual = build_factual_dossier(
        case,
        sources=sources,
        claims=claims,
        evidence=evidence,
        social_context=social_context,
        transcript_segments=transcript_segments,
        provider_coverage=provider_coverage,
    )
    if summarizer is None:
        return factual
    try:
        enriched = summarizer(factual)
    except Exception:
        return factual
    if not isinstance(enriched, dict):
        return factual
    protected = {
        "case_id",
        "primary_source",
        "earliest_known_source",
        "likely_original_source",
        "sources",
        "verified_context",
        "unverified_claims",
        "contradictions",
        "alternative_explanations",
        "evidence",
    }
    result = dict(factual)
    for key, value in enriched.items():
        if key not in protected:
            result[key] = value
    validate_dossier_evidence(result, {int(item["id"]) for item in factual["evidence"]})
    return result
