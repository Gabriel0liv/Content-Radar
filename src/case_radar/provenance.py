from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Literal


ClaimStatus = Literal["source_claimed", "corroborated", "contradicted", "unverified"]
EvidenceStance = Literal["supports", "contradicts", "context_only"]
OriginStatus = Literal["unknown", "likely", "confirmed"]


@dataclass(frozen=True)
class ProvenanceSource:
    source_id: int
    published_at: datetime | None
    platform: str | None = None
    author_handle: str | None = None
    canonical_url: str | None = None
    links_to_source_ids: tuple[int, ...] = ()
    claims_original: bool = False
    author_confirms_origin: bool = False


@dataclass(frozen=True)
class ProvenanceResult:
    earliest_known_source_id: int | None
    likely_original_source_id: int | None
    origin_status: OriginStatus
    confidence: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceInput:
    evidence_id: int
    stance: EvidenceStance
    source_id: int | None = None
    social_context_item_id: int | None = None
    transcript_segment_id: int | None = None
    independence_key: str | None = None
    evidence_kind: Literal["source", "social", "transcript", "external"] = "source"
    author_is_source_author: bool = False


@dataclass(frozen=True)
class ClaimAssessment:
    status: ClaimStatus
    confidence: float
    supporting_evidence_ids: tuple[int, ...]
    contradicting_evidence_ids: tuple[int, ...]
    reasons: tuple[str, ...]


def _source_from_any(source: ProvenanceSource | Any) -> ProvenanceSource:
    if isinstance(source, ProvenanceSource):
        return source
    if isinstance(source, dict):
        get = source.get
    else:
        get = lambda key, default=None: getattr(source, key, default)
    relation = get("relation", None) or get("relation_json", None) or {}
    linked_ids = relation.get("linked_source_ids", ()) if isinstance(relation, dict) else ()
    source_id = get("id", None)
    if source_id is None:
        source_id = get("source_id", None)
    if source_id is None:
        raise ValueError("Fonte sem id para resolução de proveniência")
    return ProvenanceSource(
        source_id=int(source_id),
        published_at=get("published_at"),
        platform=get("platform"),
        author_handle=get("author_handle"),
        canonical_url=get("canonical_url"),
        links_to_source_ids=tuple(int(value) for value in linked_ids or ()),
        claims_original=bool(get("claims_original", False)),
        author_confirms_origin=bool(get("author_confirms_origin", False)),
    )


def resolve_provenance(sources: Iterable[ProvenanceSource | Any]) -> ProvenanceResult:
    normalized = [_source_from_any(source) for source in sources]
    if not normalized:
        return ProvenanceResult(None, None, "unknown", 0.0, ("no_sources",))

    dated = [source for source in normalized if source.published_at is not None]
    earliest = min(dated, key=lambda source: source.published_at) if dated else None
    reasons: list[str] = []
    if earliest is not None:
        reasons.append("earliest_timestamp")

    incoming_links: dict[int, int] = {source.source_id: 0 for source in normalized}
    source_ids = set(incoming_links)
    for source in normalized:
        for linked_id in source.links_to_source_ids:
            if linked_id in source_ids:
                incoming_links[linked_id] += 1

    likely = None
    strongest = -1.0
    for source in normalized:
        score = 0.0
        if earliest is not None and source.source_id == earliest.source_id:
            score += 0.35
        score += min(0.35, incoming_links.get(source.source_id, 0) * 0.15)
        if source.claims_original:
            score += 0.15
        if source.author_confirms_origin:
            score += 0.35
        if score > strongest:
            likely = source
            strongest = score

    confirmed = next(
        (
            source
            for source in normalized
            if source.author_confirms_origin and incoming_links.get(source.source_id, 0) >= 1
        ),
        None,
    )

    if confirmed is not None:
        reasons.extend(("author_origin_confirmation", "linked_by_other_source"))
        return ProvenanceResult(
            earliest_known_source_id=earliest.source_id if earliest else None,
            likely_original_source_id=confirmed.source_id,
            origin_status="confirmed",
            confidence=0.95,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    if likely is not None and strongest >= 0.45:
        if incoming_links.get(likely.source_id, 0):
            reasons.append("linked_by_other_source")
        if likely.claims_original:
            reasons.append("source_claims_original")
        return ProvenanceResult(
            earliest_known_source_id=earliest.source_id if earliest else None,
            likely_original_source_id=likely.source_id,
            origin_status="likely",
            confidence=round(min(0.89, max(0.45, strongest)), 4),
            reasons=tuple(dict.fromkeys(reasons)),
        )

    return ProvenanceResult(
        earliest_known_source_id=earliest.source_id if earliest else None,
        likely_original_source_id=earliest.source_id if earliest else None,
        origin_status="unknown",
        confidence=0.25 if earliest else 0.0,
        reasons=tuple(dict.fromkeys(reasons or ["insufficient_origin_evidence"])),
    )


def assess_claim(evidence: Iterable[EvidenceInput]) -> ClaimAssessment:
    items = list(evidence)
    supports = [item for item in items if item.stance == "supports"]
    contradicts = [item for item in items if item.stance == "contradicts"]
    supporting_ids = tuple(item.evidence_id for item in supports)
    contradicting_ids = tuple(item.evidence_id for item in contradicts)

    independent_support_keys = {
        item.independence_key
        for item in supports
        if item.independence_key and item.evidence_kind in {"source", "transcript", "external"}
    }
    independent_contradict_keys = {
        item.independence_key
        for item in contradicts
        if item.independence_key and item.evidence_kind in {"source", "transcript", "external"}
    }
    author_support = any(item.author_is_source_author for item in supports)
    social_only_support = bool(supports) and all(item.evidence_kind == "social" for item in supports)

    reasons: list[str] = []
    if contradicts:
        reasons.append("contradicting_evidence_present")

    if len(independent_support_keys) >= 2 and not independent_contradict_keys:
        reasons.append("two_independent_supporting_sources")
        return ClaimAssessment("corroborated", 0.9, supporting_ids, contradicting_ids, tuple(reasons))

    if len(independent_contradict_keys) >= 2 and len(independent_support_keys) < 2:
        reasons.append("two_independent_contradicting_sources")
        return ClaimAssessment("contradicted", 0.9, supporting_ids, contradicting_ids, tuple(reasons))

    if independent_contradict_keys and independent_support_keys:
        reasons.append("material_source_conflict")
        return ClaimAssessment("contradicted", 0.65, supporting_ids, contradicting_ids, tuple(reasons))

    if author_support and supports:
        reasons.append("source_author_claim")
        return ClaimAssessment("source_claimed", 0.6, supporting_ids, contradicting_ids, tuple(reasons))

    if social_only_support:
        reasons.append("social_comment_only")
        return ClaimAssessment("unverified", 0.3, supporting_ids, contradicting_ids, tuple(reasons))

    if supports:
        reasons.append("single_supporting_source")
        return ClaimAssessment("source_claimed", 0.5, supporting_ids, contradicting_ids, tuple(reasons))

    if contradicts:
        reasons.append("contradiction_without_support")
        return ClaimAssessment("contradicted", 0.7, supporting_ids, contradicting_ids, tuple(reasons))

    return ClaimAssessment("unverified", 0.0, (), (), ("no_material_evidence",))
