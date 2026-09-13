import re
from typing import Dict, Any, List, Optional, Tuple

import httpx
import yt_dlp

from src.services.audio_transcriber import AudioTranscriber


def merge_overlapping_text(previous_text: str, current_text: str) -> str:
    if not previous_text:
        return current_text
    if not current_text:
        return ""

    prev_words = previous_text.split()
    curr_words = current_text.split()

    def clean(word: str) -> str:
        return word.strip(".,!?;;:\"'()[]{}*-–—").lower()

    prev_cleaned = [clean(w) for w in prev_words]
    curr_cleaned = [clean(w) for w in curr_words]
    for size in range(min(len(prev_cleaned), len(curr_cleaned)), 0, -1):
        if prev_cleaned[-size:] == curr_cleaned[:size]:
            return " ".join(curr_words[size:])
    return current_text


class YouTubeReferenceImporter:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def extract_metadata(self, url: str) -> Dict[str, Any]:
        with yt_dlp.YoutubeDL({
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 15,
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Não foi possível extrair metadados para a URL fornecida.")
            return info

    def clean_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {
            "id", "title", "description", "channel", "channel_id", "uploader",
            "duration", "view_count", "like_count", "upload_date", "webpage_url",
            "thumbnail", "language", "availability",
        }
        cleaned = {k: v for k, v in info.items() if k in allowed}
        cleaned["subtitles_languages"] = list((info.get("subtitles") or {}).keys())
        cleaned["automatic_captions_languages"] = list((info.get("automatic_captions") or {}).keys())
        return cleaned

    def select_caption_track(
        self,
        info: Dict[str, Any],
        preferred_languages: List[str],
        allow_auto_captions: bool,
    ) -> Optional[Tuple[str, str, str]]:
        subtitles = info.get("subtitles", {}) or {}
        automatic = info.get("automatic_captions", {}) or {}

        for lang in preferred_languages:
            matched = self._match_language(subtitles, lang)
            if matched:
                return matched, "manual_caption", self._pick_url(subtitles[matched])

        if allow_auto_captions:
            for lang in preferred_languages:
                matched = self._match_language(automatic, lang)
                if matched:
                    return matched, "auto_caption", self._pick_url(automatic[matched])
        return None

    @staticmethod
    def _match_language(tracks: Dict[str, Any], requested: str) -> Optional[str]:
        if requested in tracks:
            return requested
        base = requested.split("-")[0].lower()
        return next((key for key in tracks if key.split("-")[0].lower() == base), None)

    @staticmethod
    def _pick_url(formats: List[Dict[str, Any]]) -> str:
        for item in formats:
            if item.get("ext") == "vtt" and item.get("url"):
                return item["url"]
        for item in formats:
            if item.get("url"):
                return item["url"]
        raise ValueError("Faixa de legenda sem URL utilizável.")

    def fetch_caption_text(self, url: str) -> str:
        headers = {"User-Agent": "Mozilla/5.0"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.text

    def parse_vtt(self, vtt_text: str) -> List[Dict[str, Any]]:
        timestamp_pattern = re.compile(
            r'(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s*-->\s*'
            r'(\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})'
        )

        def parse_time(value: str) -> float:
            parts = value.replace(',', '.').split(':')
            if len(parts) == 3:
                h, m, s = parts
                return float(h) * 3600 + float(m) * 60 + float(s)
            m, s = parts
            return float(m) * 60 + float(s)

        raw: List[Dict[str, Any]] = []
        for block in re.split(r'\n\s*\n', vtt_text):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            match = None
            text_start = 0
            for idx, line in enumerate(lines[:3]):
                match = timestamp_pattern.search(line)
                if match:
                    text_start = idx + 1
                    break
            if not match:
                continue

            text_parts = []
            for line in lines[text_start:]:
                if line.startswith(('NOTE', 'STYLE', 'WEBVTT', 'Kind:', 'Language:')):
                    continue
                cleaned = re.sub(r'<[^>]+>', '', line).strip()
                if cleaned:
                    text_parts.append(cleaned)
            text = ' '.join(text_parts).strip()
            if text:
                raw.append({
                    "start_time": parse_time(match.group(1)),
                    "end_time": parse_time(match.group(2)),
                    "text": text,
                })

        cleaned: List[Dict[str, Any]] = []
        for segment in raw:
            if not cleaned:
                cleaned.append(segment.copy())
                continue
            previous = cleaned[-1]
            if segment["start_time"] < previous["end_time"]:
                new_part = merge_overlapping_text(previous["text"], segment["text"])
                overlap_words = len(segment["text"].split()) - len(new_part.split())
                if overlap_words >= 2:
                    if new_part.strip():
                        previous["text"] += " " + new_part.strip()
                    previous["end_time"] = max(previous["end_time"], segment["end_time"])
                    continue
            cleaned.append(segment.copy())

        return [{"segment_index": idx, **segment} for idx, segment in enumerate(cleaned)]

    def build_clean_full_text(self, segments: List[Dict[str, Any]]) -> str:
        if not segments:
            return ""
        ordered = sorted(segments, key=lambda item: item.get("start_time", 0.0))
        result: List[str] = []
        previous = None
        for segment in ordered:
            text = segment.get("text", "").strip()
            if not text:
                continue
            if previous is None:
                result.append(text)
            elif (
                segment.get("start_time") is not None
                and previous.get("end_time") is not None
                and segment["start_time"] < previous["end_time"]
            ):
                accumulated = " ".join(result)
                new_part = merge_overlapping_text(accumulated, text)
                if new_part:
                    result.append(new_part)
            else:
                result.append(text)
            previous = segment
        return " ".join(result)

    def normalize_audio_transcription_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for segment in segments:
            text = str(segment.get("text", "")).strip()
            if not text:
                continue
            normalized.append({
                "segment_index": len(normalized),
                "start_time": float(segment.get("start", 0.0)),
                "end_time": float(segment.get("end", segment.get("start", 0.0))),
                "text": text,
            })
        return normalized

    def build_literal_full_text(self, segments: List[Dict[str, Any]]) -> str:
        ordered = sorted(segments, key=lambda item: item.get("start_time", 0.0))
        return " ".join(item["text"].strip() for item in ordered if item.get("text", "").strip())

    def transcribe_audio_from_youtube(self, url: str) -> Dict[str, Any]:
        raw = AudioTranscriber().transcribe_youtube(url)
        segments = self.normalize_audio_transcription_segments(raw["segments"])
        if not segments:
            raise RuntimeError("Nenhuma fala foi reconhecida no áudio.")
        return {
            "language": raw.get("language"),
            "language_probability": raw.get("language_probability"),
            "model": raw.get("model"),
            "segments": segments,
            "full_text": self.build_literal_full_text(segments),
        }
