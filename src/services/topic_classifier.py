from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import json

from src.services.youtube_metadata_service import normalize_tag


CLASSIFIER_VERSION = "rules-v1"


@dataclass
class TopicSignalEvidence:
    source: str
    signal: str
    weight: float


@dataclass
class TopicClassification:
    topic: str
    confidence: float
    signals: List[TopicSignalEvidence]
    classifier_version: str = CLASSIFIER_VERSION


class TopicClassifier:
    def __init__(self, rules_path: Optional[Path] = None):
        path = rules_path or Path(__file__).resolve().parents[1] / "data" / "topic_rules.json"
        self.rules = json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _normalize_text(value: Optional[str]) -> str:
        if not value:
            return ""
        return normalize_tag(value)

    @staticmethod
    def _contains_alias(text: str, alias: str) -> bool:
        if not text:
            return False
        normalized_alias = normalize_tag(alias)
        if len(normalized_alias) <= 3:
            return normalized_alias in text.split()
        return normalized_alias in text

    def _collect_text_sources(self, item, transcript_text: Optional[str], channel_profile) -> dict:
        tags = [self._normalize_text(value) for value in (getattr(item, "youtube_tags_json", None) or [])]
        topics = [self._normalize_text(value) for value in (getattr(item, "youtube_topics_json", None) or [])]
        profile_topics = []
        if channel_profile:
            dominant = getattr(channel_profile, "dominant_topics_json", None) or []
            for value in dominant:
                if isinstance(value, dict):
                    profile_topics.append(self._normalize_text(value.get("name")))
                else:
                    profile_topics.append(self._normalize_text(str(value)))

        return {
            "youtube_tag": tags,
            "youtube_topic": topics,
            "title": [self._normalize_text(getattr(item, "title", None))],
            "description": [self._normalize_text(getattr(item, "description", None))],
            "transcript": [self._normalize_text(transcript_text)],
            "channel_profile": profile_topics,
        }

    def classify_content_item(self, item, channel_profile=None, transcript_text: Optional[str] = None) -> List[TopicClassification]:
        sources = self._collect_text_sources(item, transcript_text, channel_profile)
        results: List[TopicClassification] = []

        for topic_name, rule in self.rules.items():
            weights = rule.get("weights", {})
            aliases = rule.get("aliases", [])
            signals: List[TopicSignalEvidence] = []
            confidence = 0.0

            for source_name, texts in sources.items():
                source_weight = float(weights.get(source_name, 0.0))
                if source_weight <= 0:
                    continue
                matched_aliases = {
                    alias
                    for text in texts
                    for alias in aliases
                    if self._contains_alias(text, alias)
                }
                if matched_aliases:
                    # Multiple distinct signals from the same source should meaningfully
                    # strengthen the classification (e.g. SMP + creeper + redstone),
                    # while still using diminishing returns and a hard cap.
                    multiplier = min(1.0 + 0.55 * (len(matched_aliases) - 1), 2.25)
                    contribution = source_weight * multiplier
                    confidence += contribution
                    for alias in sorted(matched_aliases):
                        signals.append(TopicSignalEvidence(source=source_name, signal=alias, weight=source_weight))

            # Official Gaming category is only weak contextual evidence for game topics;
            # it never identifies Minecraft on its own.
            category_name = self._normalize_text(getattr(item, "youtube_category_name", None))
            if topic_name in {"Minecraft", "Modded Minecraft", "Hardcore", "SMP", "Roleplay"} and category_name == "gaming" and signals:
                confidence += 0.05
                signals.append(TopicSignalEvidence(source="youtube_category", signal="Gaming", weight=0.05))

            # A single incidental description mention is deliberately capped.
            substantive_sources = {signal.source for signal in signals if signal.source not in {"description", "youtube_category"}}
            if not substantive_sources and signals:
                confidence = min(confidence, 0.35)

            confidence = max(0.0, min(confidence, 0.99))
            if confidence >= float(rule.get("minimum_confidence", 0.5)):
                results.append(TopicClassification(topic=topic_name, confidence=round(confidence, 4), signals=signals))

        return sorted(results, key=lambda result: (-result.confidence, result.topic))
