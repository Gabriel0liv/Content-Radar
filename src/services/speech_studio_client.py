from __future__ import annotations

import os
from typing import Any

import httpx

from src.schemas.speech import (
    ResolvedSpeechSttConfig,
    SpeechEngineStatus,
    SpeechSttEngineResult,
)


class SpeechStudioError(RuntimeError):
    pass


class SpeechStudioOfflineError(SpeechStudioError):
    pass


class SpeechStudioBusyError(SpeechStudioError):
    pass


class SpeechStudioRequestError(SpeechStudioError):
    pass


class SpeechStudioClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("SPEECH_STUDIO_BASE_URL")
            or "http://host.docker.internal:8010"
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("SPEECH_STUDIO_TIMEOUT_SECONDS", "30")
        )
        self.transport = transport

    def _client(self, timeout: float | None = None) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            timeout=timeout or self.timeout_seconds,
            transport=self.transport,
        )

    def health(self) -> SpeechEngineStatus:
        try:
            with self._client() as client:
                response = client.get("/health")
                response.raise_for_status()
                details = response.json() if response.content else None
            return SpeechEngineStatus(
                online=True,
                base_url=self.base_url,
                message="Speech Studio online",
                details=details if isinstance(details, dict) else None,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
            return SpeechEngineStatus(
                online=False,
                base_url=self.base_url,
                message="Speech Studio indisponível",
            )
        except httpx.HTTPError as exc:
            return SpeechEngineStatus(
                online=False,
                base_url=self.base_url,
                message="Speech Studio respondeu com erro",
                details={"error_type": exc.__class__.__name__},
            )

    def transcribe_file(
        self,
        file_name: str,
        file_bytes: bytes,
        config: ResolvedSpeechSttConfig,
    ) -> SpeechSttEngineResult:
        form_data = self._serialize_form(config)
        files = {"file": (file_name, file_bytes, "application/octet-stream")}
        try:
            with self._client(timeout=7200.0) as client:
                response = client.post("/stt/transcribe", data=form_data, files=files)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            raise SpeechStudioOfflineError("Speech Studio está indisponível") from exc
        except httpx.HTTPError as exc:
            raise SpeechStudioRequestError("Falha ao comunicar com Speech Studio") from exc

        if response.status_code == 409:
            raise SpeechStudioBusyError(self._extract_error_message(response, "Speech Studio está ocupado"))
        if response.is_error:
            raise SpeechStudioRequestError(
                self._extract_error_message(response, f"Speech Studio retornou HTTP {response.status_code}")
            )

        payload = response.json()
        return SpeechSttEngineResult.model_validate(payload)

    @staticmethod
    def _serialize_form(config: ResolvedSpeechSttConfig) -> dict[str, str]:
        raw: dict[str, Any] = config.model_dump(exclude_none=True)
        result: dict[str, str] = {}
        for key, value in raw.items():
            if isinstance(value, bool):
                result[key] = "true" if value else "false"
            else:
                result[key] = str(value)
        return result

    @staticmethod
    def _extract_error_message(response: httpx.Response, fallback: str) -> str:
        try:
            payload = response.json()
        except ValueError:
            return fallback
        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("error") or payload.get("message")
            if detail:
                return str(detail)
        return fallback
