from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.case_radar import MediaFingerprint
from src.case_radar.url_normalization import canonicalize_url


MERGE_THRESHOLD = 0.82
SUGGEST_THRESHOLD = 0.55


@dataclass(frozen=True)
class ClusterFeatures:
    platform: str | None = None
    external_id: str | None = None
    canonical_url: str | None = None
    linked_urls: tuple[str, ...] = ()
    text: str = ""
    alleged_date: str | None = None
    alleged_location: str | None = None
    thumbnail_hash: str | None = None
    transcript_text: str = ""


@dataclass(frozen=True)
class ClusterDecision:
    score: float
    reasons: tuple[str, ...]
    action: Literal["merge", "suggest", "separate"]


def _value(source: Any, name: str, default=None):
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _normalize_text(value: str | None) -> str:
    text = re.sub(r"[^\wÀ-ÿ]+", " ", (value or "").casefold())
    return " ".join(text.split())


def _text_similarity(a: str, b: str) -> float:
    a_norm = _normalize_text(a)
    b_norm = _normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    jaccard = len(a_words & b_words) / max(1, len(a_words | b_words))
    sequence = SequenceMatcher(None, a_norm, b_norm).ratio()
    return max(jaccard, sequence)


def features_from_source(
    source: Any,
    *,
    transcript_text: str | None = None,
    thumbnail_hash: str | None = None,
) -> ClusterFeatures:
    relation = _value(source, "relation", None) or _value(source, "relation_json", None) or {}
    linked: list[str] = []
    for key in ("external_url", "linked_url", "source_url", "original_url"):
        value = relation.get(key) if isinstance(relation, dict) else None
        if value:
            linked.append(canonicalize_url(str(value)))
    text = " ".join(
        part
        for part in (
            _value(source, "title_or_caption", None),
            _value(source, "text", None),
        )
        if part
    )
    raw = _value(source, "raw_json", None) or {}
    if thumbnail_hash is None and isinstance(raw, dict):
        thumbnail_hash = raw.get("thumbnail_hash")
    return ClusterFeatures(
        platform=_value(source, "platform", None),
        external_id=_value(source, "external_id", None),
        canonical_url=canonicalize_url(_value(source, "canonical_url", "")) if _value(source, "canonical_url", None) else None,
        linked_urls=tuple(dict.fromkeys(linked)),
        text=text,
        alleged_date=_value(source, "alleged_date", None),
        alleged_location=_value(source, "alleged_location", None),
        thumbnail_hash=thumbnail_hash,
        transcript_text=transcript_text or _value(source, "transcript_text", "") or "",
    )


def compare_sources(
    left: ClusterFeatures | Any,
    right: ClusterFeatures | Any,
    *,
    merge_threshold: float = MERGE_THRESHOLD,
    suggest_threshold: float = SUGGEST_THRESHOLD,
) -> ClusterDecision:
    a = left if isinstance(left, ClusterFeatures) else features_from_source(left)
    b = right if isinstance(right, ClusterFeatures) else features_from_source(right)
    reasons: list[str] = []

    if a.platform and b.platform and a.platform == b.platform and a.external_id and a.external_id == b.external_id:
        return ClusterDecision(1.0, ("same_platform_external_id",), "merge")
    if a.canonical_url and b.canonical_url and a.canonical_url == b.canonical_url:
        return ClusterDecision(1.0, ("same_canonical_url",), "merge")

    score = 0.0
    linked_overlap = set(a.linked_urls) & set(b.linked_urls)
    if linked_overlap:
        score += 0.55
        reasons.append("shared_linked_url")
    if a.canonical_url and (a.canonical_url in b.linked_urls or b.canonical_url in a.linked_urls):
        score += 0.65
        reasons.append("source_links_to_other")

    text_similarity = _text_similarity(a.text, b.text)
    if text_similarity >= 0.88:
        score += 0.45
        reasons.append("very_similar_text")
    elif text_similarity >= 0.70:
        score += 0.30
        reasons.append("similar_text")
    elif text_similarity >= 0.52:
        score += 0.16
        reasons.append("some_text_similarity")

    transcript_similarity = _text_similarity(a.transcript_text, b.transcript_text)
    if transcript_similarity >= 0.9:
        score += 0.55
        reasons.append("very_similar_transcript")
    elif transcript_similarity >= 0.75:
        score += 0.35
        reasons.append("similar_transcript")

    if a.thumbnail_hash and b.thumbnail_hash and a.thumbnail_hash == b.thumbnail_hash:
        score += 0.60
        reasons.append("same_thumbnail_hash")

    if a.alleged_date and b.alleged_date and str(a.alleged_date) == str(b.alleged_date):
        score += 0.10
        reasons.append("same_alleged_date")
    if a.alleged_location and b.alleged_location and _normalize_text(str(a.alleged_location)) == _normalize_text(str(b.alleged_location)):
        score += 0.10
        reasons.append("same_alleged_location")

    score = round(min(1.0, score), 4)
    if score >= merge_threshold:
        action = "merge"
    elif score >= suggest_threshold:
        action = "suggest"
    else:
        action = "separate"
    return ClusterDecision(score, tuple(reasons), action)


def upsert_media_fingerprint(
    db: Session,
    *,
    source_id: int,
    fingerprint_type: str,
    fingerprint_value: str,
    algorithm: str | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> MediaFingerprint:
    existing = db.execute(
        select(MediaFingerprint).where(
            MediaFingerprint.source_id == source_id,
            MediaFingerprint.fingerprint_type == fingerprint_type,
            MediaFingerprint.fingerprint_value == fingerprint_value,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    fingerprint = MediaFingerprint(
        source_id=source_id,
        fingerprint_type=fingerprint_type,
        fingerprint_value=fingerprint_value,
        algorithm=algorithm,
        metadata_json=metadata_json or {},
    )
    db.add(fingerprint)
    db.commit()
    db.refresh(fingerprint)
    return fingerprint
