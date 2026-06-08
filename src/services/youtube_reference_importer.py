import yt_dlp
import httpx
import re
from typing import Dict, Any, List, Optional, Tuple

class YouTubeReferenceImporter:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def extract_metadata(self, url: str) -> Dict[str, Any]:
        """
        Extracts video metadata from YouTube URL using yt-dlp.
        Throws yt_dlp.utils.DownloadError or other exceptions if video is private, deleted, or network fails.
        """
        ydl_opts = {
            "skip_download": True,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "socket_timeout": 15,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Não foi possível extrair metadados para a URL fornecida.")
            return info

    def clean_metadata(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Removes large or sensitive keys from info to save a clean raw_json representation.
        """
        allowed_keys = {
            "id", "title", "description", "channel", "channel_id", "uploader",
            "duration", "view_count", "like_count", "upload_date", "webpage_url",
            "thumbnail", "language", "availability"
        }
        cleaned = {k: v for k, v in info.items() if k in allowed_keys}
        
        # Save list of available subtitle languages for diagnostic purposes
        if "subtitles" in info and isinstance(info["subtitles"], dict):
            cleaned["subtitles_languages"] = list(info["subtitles"].keys())
        else:
            cleaned["subtitles_languages"] = []
            
        if "automatic_captions" in info and isinstance(info["automatic_captions"], dict):
            cleaned["automatic_captions_languages"] = list(info["automatic_captions"].keys())
        else:
            cleaned["automatic_captions_languages"] = []
            
        return cleaned

    def select_caption_track(
        self,
        info: Dict[str, Any],
        preferred_languages: List[str],
        allow_auto_captions: bool
    ) -> Optional[Tuple[str, str, str]]:
        """
        Selects caption language, type and url.
        Returns Tuple[language, caption_type, url] or None.
        """
        subtitles = info.get("subtitles", {}) or {}
        auto_captions = info.get("automatic_captions", {}) or {}

        # 1. Check manual captions in order of preference
        for lang in preferred_languages:
            # Match direct language code or subset (e.g. 'pt' matching 'pt' or 'pt-BR')
            matched_lang = None
            if lang in subtitles:
                matched_lang = lang
            else:
                # Try finding sub-keys like pt-BR when 'pt' requested
                for k in subtitles.keys():
                    if k.split('-')[0] == lang.split('-')[0]:
                        matched_lang = k
                        break
            
            if matched_lang:
                formats = subtitles[matched_lang]
                # Look for VTT format
                for fmt in formats:
                    if fmt.get("ext") == "vtt":
                        return matched_lang, "manual_caption", fmt.get("url")
                if formats:
                    return matched_lang, "manual_caption", formats[0].get("url")

        # 2. Check automatic captions in order of preference
        if allow_auto_captions:
            for lang in preferred_languages:
                matched_lang = None
                if lang in auto_captions:
                    matched_lang = lang
                else:
                    for k in auto_captions.keys():
                        if k.split('-')[0] == lang.split('-')[0]:
                            matched_lang = k
                            break

                if matched_lang:
                    formats = auto_captions[matched_lang]
                    for fmt in formats:
                        if fmt.get("ext") == "vtt":
                            return matched_lang, "auto_caption", fmt.get("url")
                    if formats:
                        return matched_lang, "auto_caption", formats[0].get("url")

        return None

    def fetch_caption_text(self, url: str) -> str:
        """
        Downloads the VTT subtitle content from the YouTube URL using httpx.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=self.timeout) as client:
            res = client.get(url, headers=headers)
            res.raise_for_status()
            return res.text

    def parse_vtt(self, vtt_text: str) -> List[Dict[str, Any]]:
        """
        Parses a WebVTT file, extracts clean timestamps and content,
        and applies an overlap-removal algorithm to clean up rolling/auto-captions.
        """
        blocks = re.split(r'\n\s*\n', vtt_text)
        raw_segments = []
        
        timestamp_pattern = re.compile(
            r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})'
        )
        
        def parse_time(time_str: str) -> float:
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return float(h) * 3600 + float(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return float(m) * 60 + float(s)
            return 0.0

        for block in blocks:
            lines = [line.strip() for line in block.split('\n') if line.strip()]
            if not lines:
                continue
                
            match = None
            text_start_idx = 1
            for idx in range(min(len(lines), 3)):
                m = timestamp_pattern.search(lines[idx])
                if m:
                    match = m
                    text_start_idx = idx + 1
                    break
                    
            if not match:
                continue
                
            start_t = parse_time(match.group(1))
            end_t = parse_time(match.group(2))
            
            text_lines = []
            for line in lines[text_start_idx:]:
                if line.startswith('NOTE') or line.startswith('STYLE') or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                    continue
                # Strip simple tags like <c>, <b>, <i>, <u>
                cleaned = re.sub(r'<[^>]+>', '', line).strip()
                if cleaned:
                    text_lines.append(cleaned)
                    
            text = ' '.join(text_lines).strip()
            if not text:
                continue
                
            raw_segments.append({
                'start_time': start_t,
                'end_time': end_t,
                'text': text
            })
            
        # Clean rolling/auto captions
        cleaned_segments = []
        for seg in raw_segments:
            text = seg['text']
            
            # Exact duplicate text
            if cleaned_segments and cleaned_segments[-1]['text'] == text:
                cleaned_segments[-1]['end_time'] = max(cleaned_segments[-1]['end_time'], seg['end_time'])
                continue
                
            # Rolling text build-up: if current text starts with previous text
            # and is close enough in time, update previous text and extend end time.
            if (cleaned_segments and 
                text.startswith(cleaned_segments[-1]['text']) and 
                (seg['start_time'] - cleaned_segments[-1]['end_time'] < 1.5)):
                cleaned_segments[-1]['text'] = text
                cleaned_segments[-1]['end_time'] = max(cleaned_segments[-1]['end_time'], seg['end_time'])
                continue
                
            cleaned_segments.append(seg)
            
        # Format final segment list
        final_segments = []
        for idx, seg in enumerate(cleaned_segments):
            final_segments.append({
                'segment_index': idx,
                'start_time': seg['start_time'],
                'end_time': seg['end_time'],
                'text': seg['text']
            })
            
        return final_segments
