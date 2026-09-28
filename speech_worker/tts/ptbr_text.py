from __future__ import annotations

import re
import unicodedata
from typing import Any


_WORD_FIXES: tuple[tuple[str, str], ...] = (
    ("validacao", "validação"),
    ("diarizacao", "diarização"),
    ("transcricao", "transcrição"),
    ("descricao", "descrição"),
    ("configuracao", "configuração"),
    ("pronuncia", "pronúncia"),
    ("pronuncias", "pronúncias"),
    ("sintese", "síntese"),
    ("musica", "música"),
    ("publico", "público"),
    ("numero", "número"),
    ("numeros", "números"),
    ("audio", "áudio"),
    ("audios", "áudios"),
    ("video", "vídeo"),
    ("videos", "vídeos"),
    ("portugues", "português"),
    ("ingles", "inglês"),
    ("frances", "francês"),
    ("japones", "japonês"),
    ("tambem", "também"),
    ("entao", "então"),
    ("porem", "porém"),
    ("rapido", "rápido"),
    ("rapida", "rápida"),
    ("facil", "fácil"),
    ("dificil", "difícil"),
    ("possivel", "possível"),
    ("voce", "você"),
    ("voces", "vocês"),
    ("ola", "Olá"),
    ("nao", "não"),
    ("propria", "própria"),
    ("proprio", "próprio"),
    ("proprios", "próprios"),
    ("proprias", "próprias"),
    ("unico", "único"),
    ("unica", "única"),
    ("ultima", "última"),
    ("ultimo", "último"),
    ("otimo", "ótimo"),
    ("otima", "ótima"),
    ("logico", "lógico"),
    ("logica", "lógica"),
    ("classico", "clássico"),
    ("classica", "clássica"),
    ("automatico", "automático"),
    ("automatica", "automática"),
    ("especifico", "específico"),
    ("especifica", "específica"),
    ("pratico", "prático"),
    ("pratica", "prática"),
)


def _strip_accents(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def analyze_ptbr_text(text: str) -> dict[str, Any]:
    original = text
    warnings: list[str] = []
    suggestions: list[dict[str, str]] = []

    if not text or not text.strip():
        return {
            "original_text": original,
            "normalized_text": original,
            "warnings": [],
            "suggestions": [],
            "has_issues": False,
        }

    compact = text.replace(" ", "").replace("\n", "")
    word_count = len(text.split())
    accented_chars = sum(
        1
        for char in text
        if unicodedata.category(char) in ("Ll", "Lu", "Lt", "Lm", "Lo")
        and char != _strip_accents(char)
    )
    if len(compact) > 30 and word_count > 5 and accented_chars / max(len(compact), 1) < 0.01:
        warnings.append("O texto parece ter poucos ou nenhum acento em PT-BR.")
    if compact and compact == compact.lower() and len(compact) > 15:
        warnings.append("O texto está completamente em letras minúsculas.")
    if word_count > 20 and not any(char in text for char in ".,;:!?…"):
        warnings.append("O texto longo tem pouca pontuação; isso pode prejudicar pausas e entonação.")
    long_sentences = [part for part in re.split(r"[.!?…]+", text) if len(part.split()) > 40]
    if long_sentences:
        warnings.append(f"{len(long_sentences)} frase(s) com mais de 40 palavras detectada(s).")

    words_lower = {word.lower().strip(".,;:!?\"'()[]") for word in text.split()}
    for unaccented, accented in _WORD_FIXES:
        if unaccented in words_lower:
            suggestions.append(
                {
                    "original": unaccented,
                    "suggested": accented,
                    "note": f"'{unaccented}' -> '{accented}'",
                }
            )
    if suggestions:
        warnings.append("Foram detectadas palavras conhecidas sem acentuação adequada para síntese.")

    return {
        "original_text": original,
        "normalized_text": original,
        "warnings": warnings,
        "suggestions": suggestions,
        "has_issues": bool(warnings),
    }


def normalize_ptbr_text(text: str) -> str:
    """Apply only conservative, known whole-word PT-BR replacements."""
    if not text or not text.strip():
        return text

    result = text
    for unaccented, accented in _WORD_FIXES:
        pattern = r"(?<![A-Za-zÀ-ÿ])" + re.escape(unaccented) + r"(?![A-Za-zÀ-ÿ])"

        def replace(match: re.Match[str], replacement: str = accented) -> str:
            original = match.group(0)
            if original.isupper():
                return replacement.upper()
            if original[0].isupper() and replacement[0].islower():
                return replacement[0].upper() + replacement[1:]
            return replacement

        result = re.sub(pattern, replace, result, flags=re.IGNORECASE)
    return result


# Compatibility name used by the legacy Speech Studio implementation.
normalize_basic_ptbr_text = normalize_ptbr_text
