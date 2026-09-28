from __future__ import annotations

import re


def chunk_text(text: str, max_chars: int = 400) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars deve ser maior que zero")
    if not text or not text.strip():
        return []

    normalized = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    chunks: list[str] = []
    current = ""

    def append_piece(piece: str) -> None:
        nonlocal current
        piece = piece.strip()
        if not piece:
            return
        if not current:
            current = piece
            return
        candidate = f"{current} {piece}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = piece

    def split_words(piece: str) -> list[str]:
        words = piece.split()
        result: list[str] = []
        buffer = ""
        for word in words:
            if not buffer:
                buffer = word
                continue
            candidate = f"{buffer} {word}"
            if len(candidate) <= max_chars:
                buffer = candidate
            else:
                result.append(buffer)
                buffer = word
        if buffer:
            result.append(buffer)
        return result

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_chars:
            append_piece(sentence)
            continue

        if current:
            chunks.append(current)
            current = ""
        clauses = re.split(r"(?<=[,;:—])\s+", sentence)
        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue
            if len(clause) <= max_chars:
                append_piece(clause)
            else:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(split_words(clause))

    if current:
        chunks.append(current)
    return [item for item in chunks if item]
