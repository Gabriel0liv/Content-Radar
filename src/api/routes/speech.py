from __future__ import annotations

from fastapi import APIRouter

from src.schemas.speech import SpeechSttOptions
from src.services.speech_presets import list_builtin_stt_presets, resolve_stt_config
from src.services.speech_studio_client import SpeechStudioClient


router = APIRouter()


def get_speech_studio_client() -> SpeechStudioClient:
    return SpeechStudioClient()


@router.get("/status")
def get_status():
    return get_speech_studio_client().health()


@router.get("/stt/presets")
def get_stt_presets():
    return {"presets": list_builtin_stt_presets()}


@router.post("/stt/resolve")
def resolve_stt(options: SpeechSttOptions):
    resolved = resolve_stt_config(options)
    return {
        "options": options,
        "resolved": resolved,
    }
