from __future__ import annotations

from typing import Any

from speech_worker.stt.types import NormalizedSegment, NormalizedTranscriptResult, NormalizedWord


def _speaker_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "UNKNOWN":
        return None
    return text


def normalize_whisperx_result(
    raw: dict[str, Any],
    *,
    model: str,
    diarized: bool,
    alignment_used: bool,
    warnings: list[str] | None = None,
) -> NormalizedTranscriptResult:
    normalized: list[NormalizedSegment] = []
    source_segments = list(raw.get("segments") or [])

    indexed = list(enumerate(source_segments))
    indexed.sort(
        key=lambda pair: (
            float(pair[1].get("start")) if pair[1].get("start") is not None else float("inf"),
            pair[0],
        )
    )

    for original_index, segment in indexed:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        words: list[NormalizedWord] = []
        for raw_word in segment.get("words") or []:
            word_text = str(raw_word.get("word") or "").strip()
            if not word_text:
                continue
            score = raw_word.get("score")
            if score is None:
                score = raw_word.get("probability")
            words.append(
                NormalizedWord(
                    word=word_text,
                    start=float(raw_word["start"]) if raw_word.get("start") is not None else None,
                    end=float(raw_word["end"]) if raw_word.get("end") is not None else None,
                    score=float(score) if score is not None else None,
                    speaker=_speaker_or_none(raw_word.get("speaker")),
                )
            )
        normalized.append(
            NormalizedSegment(
                index=len(normalized),
                start=float(segment["start"]) if segment.get("start") is not None else None,
                end=float(segment["end"]) if segment.get("end") is not None else None,
                text=text,
                speaker=_speaker_or_none(segment.get("speaker")),
                words=words,
            )
        )

    full_text = " ".join(segment.text for segment in normalized).strip()
    raw_metadata: dict[str, Any] = {}
    for key in ("language", "language_probability", "duration"):
        value = raw.get(key)
        if isinstance(value, (str, int, float, bool)) or value is None:
            raw_metadata[key] = value

    return NormalizedTranscriptResult(
        language=str(raw.get("language")) if raw.get("language") else None,
        model=model,
        full_text=full_text,
        segments=normalized,
        diarized=diarized,
        alignment_used=alignment_used,
        warnings=list(warnings or []),
        raw_metadata=raw_metadata,
    )
