from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable

from src.case_radar.types import SocialContextRecord


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_REACTION_ONLY_RE = re.compile(
    r"^(?:[\W_]*|(?:kkk+|lol+|lmao+|omg+|wow+|creepy+|scary+|medo+|assustador+|wtf+)[\W_]*)$",
    re.IGNORECASE,
)

_VOCABULARY = {
    "origin": (
        "original source", "original post", "source is", "first posted", "fonte original", "post original",
        "primeiro post", "origem", "fuente original", "publicación original", "primero publicado",
    ),
    "context": (
        "recorded in", "filmed in", "happened in", "this was in", "gravado em", "filmado em", "aconteceu em",
        "isso foi em", "ocurrió en", "grabado en", "esto fue en",
    ),
    "correction": (
        "actually", "correction", "not from", "não foi", "na verdade", "correção", "en realidad", "corrección",
        "no fue",
    ),
    "debunk": (
        "debunk", "fake", "staged", "hoax", "costume", "cgi", "short film", "falso", "encenado", "montagem",
        "desmentido", "fantasia", "filme curto", "montaje", "engaño", "cortometraje",
    ),
    "witness_claim": (
        "i was there", "i saw this", "i live there", "eu estava lá", "eu vi isso", "eu moro lá", "yo estaba allí",
        "yo vi esto", "vivo allí",
    ),
    "technical_explanation": (
        "reflection", "lens", "compression", "artifact", "camera", "animal", "perspective", "reflexo", "lente",
        "compressão", "artefato", "câmera", "animal", "perspectiva", "reflejo", "compresión", "cámara",
    ),
}


@dataclass(frozen=True)
class RankedSocialItem:
    item: SocialContextRecord
    categories: frozenset[str]
    score: float


def classify_social_item(
    text: str,
    *,
    author_reply: bool = False,
    pinned: bool = False,
    language: str | None = None,
) -> set[str]:
    del pinned, language  # reserved signals for future language-specific classifiers
    normalized = " ".join((text or "").casefold().split())
    categories: set[str] = set()
    if _URL_RE.search(text or ""):
        categories.add("link")
    if author_reply:
        categories.add("author_response")
    if _YEAR_RE.search(normalized):
        categories.add("context")
    for category, phrases in _VOCABULARY.items():
        if any(phrase in normalized for phrase in phrases):
            categories.add(category)
    return categories


def _semantic_overlap(text: str, questions: Iterable[str]) -> float:
    words = {word for word in re.findall(r"[\wÀ-ÿ]{3,}", text.casefold())}
    if not words:
        return 0.0
    best = 0.0
    for question in questions:
        q_words = {word for word in re.findall(r"[\wÀ-ÿ]{3,}", question.casefold())}
        if not q_words:
            continue
        best = max(best, len(words & q_words) / max(1, len(q_words)))
    return min(1.0, best)


def score_social_item(item: SocialContextRecord, unresolved_questions: Iterable[str] = ()) -> float:
    categories = classify_social_item(
        item.body,
        author_reply=item.author_reply,
        pinned=item.pinned,
    )
    score = 0.0
    weights = {
        "link": 2.5,
        "origin": 2.2,
        "correction": 1.8,
        "debunk": 1.8,
        "context": 1.5,
        "author_response": 2.5,
        "witness_claim": 1.0,
        "technical_explanation": 1.5,
    }
    score += sum(weights.get(category, 0.0) for category in categories)
    if item.pinned:
        score += 1.0
    if item.author_reply:
        score += 0.5
    engagement = sum(max(0, int(value)) for value in item.engagement.values())
    score += min(1.5, math.log1p(engagement) * 0.22)
    body_length = len(" ".join(item.body.split()))
    score += min(0.8, body_length / 300.0)
    score += 1.5 * _semantic_overlap(item.body, unresolved_questions)
    score -= min(0.4, max(0, item.depth) * 0.05)
    if _REACTION_ONLY_RE.match(item.body.strip()):
        score -= 2.0
    return round(max(0.0, score), 4)


def select_social_context(
    items: list[SocialContextRecord],
    limit: int,
    unresolved_questions: Iterable[str] = (),
) -> list[RankedSocialItem]:
    if limit <= 0 or not items:
        return []
    ranked_by_id: dict[str, RankedSocialItem] = {}
    ranked_all: list[RankedSocialItem] = []
    for item in items:
        ranked = RankedSocialItem(
            item=item,
            categories=frozenset(
                classify_social_item(
                    item.body,
                    author_reply=item.author_reply,
                    pinned=item.pinned,
                )
            ),
            score=score_social_item(item, unresolved_questions),
        )
        ranked_all.append(ranked)
        if item.platform_item_id:
            ranked_by_id[item.platform_item_id] = ranked
            ranked_by_id[f"t1_{item.platform_item_id}"] = ranked

    ranked_all.sort(key=lambda entry: (-entry.score, entry.item.depth, entry.item.platform_item_id or ""))
    selected: list[RankedSocialItem] = []
    selected_ids: set[int] = set()

    def add_with_parents(entry: RankedSocialItem) -> None:
        chain: list[RankedSocialItem] = []
        cursor = entry
        visited: set[str] = set()
        while cursor.item.parent_id and cursor.item.parent_id not in visited:
            visited.add(cursor.item.parent_id)
            parent = ranked_by_id.get(cursor.item.parent_id)
            if parent is None:
                break
            chain.append(parent)
            cursor = parent
        for ancestor in reversed(chain):
            marker = id(ancestor.item)
            if marker not in selected_ids and len(selected) < limit:
                selected.append(ancestor)
                selected_ids.add(marker)
        marker = id(entry.item)
        if marker not in selected_ids and len(selected) < limit:
            selected.append(entry)
            selected_ids.add(marker)

    for entry in ranked_all:
        if len(selected) >= limit:
            break
        add_with_parents(entry)
    return selected
