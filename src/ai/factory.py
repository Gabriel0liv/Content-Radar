from __future__ import annotations

import os

from dotenv import load_dotenv

from src.ai.base import BaseAIProvider
from src.ai.gemini_provider import GeminiProvider
from src.ai.groq_provider import GroqProvider
from src.ai.ollama_provider import OllamaProvider
from src.ai.openai_provider import OpenAIProvider
from src.ai.openrouter_provider import OpenRouterProvider


def get_ai_provider() -> BaseAIProvider:
    load_dotenv()

    provider_name = os.getenv("AI_PROVIDER", "gemini").strip().lower() or "gemini"

    if provider_name == "ollama":
        return OllamaProvider()

    if provider_name == "openrouter":
        return OpenRouterProvider()

    if provider_name == "groq":
        return GroqProvider()

    if provider_name == "openai":
        return OpenAIProvider()

    return GeminiProvider()
