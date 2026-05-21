from __future__ import annotations

import json
import os

import requests

from src.ai.base import BaseAIProvider
from src.ai.json_utils import extract_json, normalize_analysis, normalize_batch_analysis
from src.ai.prompts import (
    ANALYSIS_SYSTEM_PROMPT,
    build_batch_video_prompt,
    build_single_video_prompt,
)


class OllamaProvider(BaseAIProvider):
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        mode: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.mode = (mode or os.getenv("OLLAMA_MODE", "cloud_direct")).strip().lower()
        model_name = model or os.getenv("OLLAMA_MODEL", "gpt-oss:120b")
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY", "")

        if self.mode == "cloud_direct":
            default_base_url = "https://ollama.com"
            if not self.api_key:
                raise RuntimeError(
                    "Falta OLLAMA_API_KEY no arquivo .env para OLLAMA_MODE=cloud_direct"
                )
        elif self.mode in {"cloud_daemon", "local"}:
            default_base_url = "http://localhost:11434"
        else:
            raise RuntimeError(
                "OLLAMA_MODE inválido. Use: cloud_direct, cloud_daemon ou local"
            )

        base_url = base_url or os.getenv("OLLAMA_BASE_URL", default_base_url)
        super().__init__(provider_name="ollama", model_name=model_name)
        self.base_url = base_url.rstrip("/")

    def _post_prompt(self, prompt: str) -> str:
        if self.mode in {"cloud_direct", "cloud_daemon"}:
            return self._post_chat(prompt)
        return self._post_generate(prompt)

    def _post_chat(self, prompt: str) -> str:
        headers = {}
        if self.mode == "cloud_direct":
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                headers=headers,
                timeout=180,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            if self.mode == "cloud_daemon":
                raise RuntimeError(
                    "Ollama daemon não está disponível. Rode ollama signin, ollama pull <modelo-cloud> e mantenha o Ollama aberto."
                ) from exc
            raise RuntimeError(f"Falha ao chamar Ollama Cloud: {exc}") from exc

        data = response.json()
        return self._extract_response_text(data)

    def _post_generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
                timeout=120,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                "Ollama não está disponível. Rode: ollama serve"
            ) from exc

        data = response.json()
        return self._extract_response_text(data)

    def _extract_response_text(self, data: dict) -> str:
        message = data.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content

        response_text = data.get("response")
        if isinstance(response_text, str) and response_text.strip():
            return response_text

        return json.dumps(data, ensure_ascii=False)

    def analyze_video_opportunity(self, video: dict) -> dict:
        prompt = build_single_video_prompt(video)
        response_text = self._post_prompt(prompt)
        parsed = extract_json(response_text)
        parsed["video_id"] = str(video.get("video_id", "")).strip()
        parsed["raw_json"] = response_text
        normalized = normalize_analysis(parsed)
        normalized["video_id"] = parsed["video_id"]
        normalized["raw_json"] = parsed["raw_json"]
        return normalized

    def analyze_video_opportunities_batch(self, videos: list[dict]) -> list[dict]:
        if not videos:
            return []

        prompt = build_batch_video_prompt(videos)
        response_text = self._post_prompt(prompt)
        parsed = extract_json(response_text)
        analyses = normalize_batch_analysis(parsed, videos)

        for analysis in analyses:
            if not analysis.get("raw_json"):
                analysis["raw_json"] = response_text

        return analyses
