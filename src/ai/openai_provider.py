from __future__ import annotations

import json
import os

from src.ai.base import BaseAIProvider
from src.ai.json_utils import extract_json, normalize_analysis
from src.ai.prompts import ANALYSIS_SYSTEM_PROMPT, build_single_video_prompt


class OpenAIProvider(BaseAIProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        model_name = model or os.getenv("OPENAI_MODEL", "")
        if not api_key:
            raise RuntimeError("Falta OPENAI_API_KEY no arquivo .env")
        if not model_name:
            raise RuntimeError("Falta OPENAI_MODEL no arquivo .env")

        super().__init__(provider_name="openai", model_name=model_name)
        self.api_key = api_key

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Pacote openai não encontrado. Rode: python -m pip install openai"
            ) from exc

        return OpenAI(api_key=self.api_key)

    def analyze_video_opportunity(self, video: dict) -> dict:
        prompt = build_single_video_prompt(video)
        client = self._client()

        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content = response.choices[0].message.content
        except Exception:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content

        parsed = content if isinstance(content, dict) else extract_json(str(content))
        parsed["video_id"] = str(video.get("video_id", "")).strip()
        parsed["raw_json"] = json.dumps(parsed, ensure_ascii=False)
        normalized = normalize_analysis(parsed)
        normalized["video_id"] = parsed["video_id"]
        normalized["raw_json"] = parsed["raw_json"]
        return normalized
