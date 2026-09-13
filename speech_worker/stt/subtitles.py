from __future__ import annotations

import json
from typing import Any


def format_timestamp(seconds: float | None, *, include_ms: bool = True, ms_separator: str = ",") -> str:
    seconds = max(0.0, float(seconds or 0.0))
    total_ms = int(round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, milliseconds = divmod(rem, 1000)
    if include_ms:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{ms_separator}{milliseconds:03d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_words_into_lines(words: list[str], max_chars: int = 42) -> list[str]:
    lines: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in [w.strip() for w in words if w and w.strip()]:
        added = len(word) + (1 if current else 0)
        if current and current_len + added > max_chars:
            lines.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += added
    if current:
        lines.append(" ".join(current))
    return lines


def group_words_into_cards(
    words: list[dict[str, Any]],
    *,
    max_lines: int = 2,
    max_chars: int = 42,
    min_duration: float = 1.0,
    max_duration: float = 6.0,
    silence_gap: float = 1.5,
) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    def normalized_word(raw: dict[str, Any], fallback_start: float = 0.0) -> dict[str, Any] | None:
        text = str(raw.get("word") or "").strip()
        if not text:
            return None
        start = raw.get("start")
        end = raw.get("end")
        start = float(start) if start is not None else fallback_start
        end = float(end) if end is not None else start + 0.5
        return {"word": text, "start": start, "end": max(start, end), "speaker": raw.get("speaker")}

    def flush() -> None:
        nonlocal current
        if not current:
            return
        start = current[0]["start"]
        end = current[-1]["end"]
        end = max(end, start + min_duration)
        cards.append(
            {
                "start": start,
                "end": end,
                "speaker": current[0].get("speaker"),
                "lines": format_words_into_lines([item["word"] for item in current], max_chars),
            }
        )
        current = []

    for raw in words:
        fallback = current[-1]["end"] if current else 0.0
        item = normalized_word(raw, fallback)
        if item is None:
            continue
        if not current:
            current = [item]
            continue

        same_speaker = item.get("speaker") == current[0].get("speaker")
        gap = item["start"] - current[-1]["end"]
        would_end = item["end"] - current[0]["start"]
        candidate_lines = format_words_into_lines([x["word"] for x in current] + [item["word"]], max_chars)
        should_split = (
            not same_speaker
            or gap > silence_gap
            or would_end > max_duration
            or len(candidate_lines) > max_lines
        )
        if should_split:
            flush()
        current.append(item)
    flush()
    return cards


def split_segment_without_words(
    text: str,
    start: float | None,
    end: float | None,
    speaker: str | None = None,
    *,
    max_lines: int = 2,
    max_chars: int = 42,
    min_duration: float = 1.0,
    max_duration: float = 6.0,
) -> list[dict[str, Any]]:
    words = [word for word in text.split() if word]
    if not words:
        return []
    start_value = float(start or 0.0)
    end_value = float(end if end is not None else start_value + min_duration)
    end_value = max(end_value, start_value + 0.01)
    lines = format_words_into_lines(words, max_chars)
    if len(lines) <= max_lines and end_value - start_value <= max_duration:
        return [{"start": start_value, "end": max(end_value, start_value + min_duration), "speaker": speaker, "lines": lines}]

    weights = [max(1, len(word)) for word in words]
    total_weight = sum(weights)
    cursor = start_value
    simulated: list[dict[str, Any]] = []
    for word, weight in zip(words, weights):
        duration = (end_value - start_value) * (weight / total_weight)
        simulated.append({"word": word, "start": cursor, "end": cursor + duration, "speaker": speaker})
        cursor += duration
    return group_words_into_cards(
        simulated,
        max_lines=max_lines,
        max_chars=max_chars,
        min_duration=min_duration,
        max_duration=max_duration,
    )


def cards_from_segments(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for segment in segments:
        words = segment.get("words") or []
        if words:
            cards.extend(group_words_into_cards(words))
        else:
            cards.extend(
                split_segment_without_words(
                    str(segment.get("text") or ""),
                    segment.get("start"),
                    segment.get("end"),
                    segment.get("speaker"),
                )
            )
    return cards


def format_card_for_subtitle(card: dict[str, Any], speaker_map: dict[str, str] | None = None, *, show_speaker: bool = True) -> str:
    lines = list(card.get("lines") or [])
    if not lines:
        return ""
    speaker = card.get("speaker")
    if show_speaker and speaker:
        speaker_name = speaker_map.get(speaker, speaker) if speaker_map else speaker
        combined = f"{speaker_name}: {' '.join(lines)}"
        lines = format_words_into_lines(combined.split(), 42)[:2]
    return "\n".join(lines)


def render_txt(segments: list[dict[str, Any]], speaker_map: dict[str, str] | None = None) -> str:
    blocks: list[str] = []
    current_speaker: str | None = None
    current_text: list[str] = []
    block_start = 0.0

    def flush() -> None:
        if current_text:
            label = current_speaker or "FALA"
            blocks.append(f"[{format_timestamp(block_start, include_ms=False)}] {label}:\n{' '.join(current_text)}")

    for segment in segments:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        raw_speaker = segment.get("speaker")
        speaker = speaker_map.get(raw_speaker, raw_speaker) if speaker_map and raw_speaker else raw_speaker
        if current_text and speaker != current_speaker:
            flush()
            current_text = []
        if not current_text:
            block_start = float(segment.get("start") or 0.0)
            current_speaker = speaker
        current_text.append(text)
    flush()
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def render_srt(cards: list[dict[str, Any]], speaker_map: dict[str, str] | None = None, *, show_speaker: bool = True) -> str:
    chunks: list[str] = []
    for index, card in enumerate(cards, 1):
        chunks.append(
            f"{index}\n{format_timestamp(card.get('start'), ms_separator=',')} --> {format_timestamp(card.get('end'), ms_separator=',')}\n"
            f"{format_card_for_subtitle(card, speaker_map, show_speaker=show_speaker)}"
        )
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def render_vtt(cards: list[dict[str, Any]], speaker_map: dict[str, str] | None = None, *, show_speaker: bool = True) -> str:
    chunks = ["WEBVTT"]
    for card in cards:
        chunks.append(
            f"{format_timestamp(card.get('start'), ms_separator='.')} --> {format_timestamp(card.get('end'), ms_separator='.')}\n"
            f"{format_card_for_subtitle(card, speaker_map, show_speaker=show_speaker)}"
        )
    return "\n\n".join(chunks) + "\n"


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
