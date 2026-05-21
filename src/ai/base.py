from __future__ import annotations

import json
from abc import ABC, abstractmethod

from src.ai.json_utils import normalize_batch_analysis


class BaseAIProvider(ABC):
    provider_name: str
    model_name: str

    def __init__(self, provider_name: str, model_name: str) -> None:
        self.provider_name = provider_name
        self.model_name = model_name

    @abstractmethod
    def analyze_video_opportunity(self, video: dict) -> dict:
        raise NotImplementedError

    def analyze_video_opportunities_batch(self, videos: list[dict]) -> list[dict]:
        results: list[dict] = []

        for video in videos:
            try:
                analysis = self.analyze_video_opportunity(video)
            except Exception as exc:
                reason = f"Falha ao analisar este vídeo: {exc}"
                analysis = {
                    "video_id": str(video.get("video_id", "")).strip(),
                    "is_good_reference": False,
                    "detected_language": "unknown",
                    "real_niche": "",
                    "content_type": "",
                    "hook_type": "",
                    "retention_pattern": "",
                    "dark_channel_fit": 0,
                    "production_difficulty": "medium",
                    "copyright_risk": "medium",
                    "reused_content_risk": "medium",
                    "fact_check_needed": False,
                    "opportunity_reason": reason,
                    "original_angle_ideas": [],
                    "raw_json": json.dumps(
                        {"video_id": video.get("video_id"), "reason": reason},
                        ensure_ascii=False,
                    ),
                }

            if not analysis.get("video_id") and video.get("video_id"):
                analysis["video_id"] = video["video_id"]

            results.append(analysis)

        return normalize_batch_analysis({"analyses": results}, videos)
