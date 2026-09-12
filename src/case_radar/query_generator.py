from __future__ import annotations

from dataclasses import dataclass

from src.case_radar.types import Platform, ResearchDepth
from src.schemas.case_radar import CaseResearchCreate


@dataclass(frozen=True)
class GeneratedQuery:
    language: str
    intent: str
    query_text: str
    target_platforms: tuple[Platform, ...]


_LANGUAGE_PATTERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "pt": {
        "core": ("{theme}", "{theme} vídeo caso"),
        "source_hunt": ("{theme} fonte original", "{theme} primeiro vídeo postagem original"),
        "context": ("{theme} contexto origem local data", "{theme} história contexto completo"),
        "debunk": ("{theme} explicação desmentido falso encenado", "{theme} análise o que aconteceu"),
        "local_language": ("{theme} caso misterioso", "{theme} vídeo estranho"),
    },
    "en": {
        "core": ("{theme}", "{theme} video case"),
        "source_hunt": ("{theme} original source", "{theme} earliest upload original post"),
        "context": ("{theme} context origin location date", "{theme} full story context"),
        "debunk": ("{theme} debunk explanation fake hoax", "{theme} analysis what happened"),
        "local_language": ("{theme} mystery case", "{theme} strange footage"),
    },
    "es": {
        "core": ("{theme}", "{theme} video caso"),
        "source_hunt": ("{theme} fuente original", "{theme} primera publicación video original"),
        "context": ("{theme} contexto origen lugar fecha", "{theme} historia contexto completo"),
        "debunk": ("{theme} explicación desmentido falso montaje", "{theme} análisis qué pasó"),
        "local_language": ("{theme} caso misterioso", "{theme} video extraño"),
    },
}

_DEPTH_VARIANTS: dict[ResearchDepth, int] = {
    "quick": 1,
    "balanced": 1,
    "deep": 2,
}

_DEPTH_INTENTS: dict[ResearchDepth, tuple[str, ...]] = {
    "quick": ("core", "source_hunt", "context"),
    "balanced": ("core", "source_hunt", "context", "debunk", "local_language"),
    "deep": ("core", "source_hunt", "context", "debunk", "local_language"),
}


def _normalize_query(value: str) -> str:
    return " ".join(value.split()).strip()


def _patterns_for_language(language: str) -> dict[str, tuple[str, ...]]:
    if language in _LANGUAGE_PATTERNS:
        return _LANGUAGE_PATTERNS[language]
    return {
        "core": ("{theme}", "{theme} video"),
        "source_hunt": ("{theme} original source", "{theme} original post"),
        "context": ("{theme} context", "{theme} origin"),
        "debunk": ("{theme} explanation", "{theme} debunk"),
        "local_language": ("{theme} case", "{theme} footage"),
    }


def generate_queries(request: CaseResearchCreate) -> list[GeneratedQuery]:
    include_suffix = " ".join(request.include_terms).strip()
    result: list[GeneratedQuery] = []
    seen: set[tuple[str, str, str]] = set()
    variants_per_intent = _DEPTH_VARIANTS[request.research_depth]
    intents = _DEPTH_INTENTS[request.research_depth]
    include_applied = False

    for language in request.languages:
        patterns = _patterns_for_language(language)
        for intent in intents:
            templates = patterns[intent][:variants_per_intent]
            for template in templates:
                text = _normalize_query(template.format(theme=request.theme))
                if include_suffix and not include_applied:
                    text = _normalize_query(f"{text} {include_suffix}")
                    include_applied = True
                key = (language, intent, text.casefold())
                if not text or key in seen:
                    continue
                seen.add(key)
                result.append(
                    GeneratedQuery(
                        language=language,
                        intent=intent,
                        query_text=text,
                        target_platforms=tuple(request.platforms),
                    )
                )

    if include_suffix and not include_applied and result:
        first = result[0]
        replaced = GeneratedQuery(
            language=first.language,
            intent=first.intent,
            query_text=_normalize_query(f"{first.query_text} {include_suffix}"),
            target_platforms=first.target_platforms,
        )
        result[0] = replaced

    return result
