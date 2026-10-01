from __future__ import annotations

from typing import Any


def _check(check_id: str, status: str, reason: str, action: str | None = None) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "reason": reason,
        "action": action,
    }


def build_diagnostics(capabilities: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    if capabilities.get("ffmpeg_available"):
        checks.append(_check("ffmpeg", "ok", "FFmpeg disponível."))
    else:
        checks.append(
            _check(
                "ffmpeg",
                "error",
                "FFmpeg não foi encontrado; conversão STT e exportação MP3 ficam indisponíveis.",
                "Instale o FFmpeg e deixe o executável disponível no PATH do speech worker.",
            )
        )

    if capabilities.get("espeak_available"):
        checks.append(_check("espeak", "ok", "eSpeak disponível."))
    else:
        checks.append(
            _check(
                "espeak",
                "error",
                "eSpeak/eSpeak NG não foi encontrado; motores TTS que dependem dele podem ficar indisponíveis.",
                "Instale o eSpeak NG e deixe o executável disponível no PATH do speech worker.",
            )
        )

    if capabilities.get("cuda_available"):
        gpu = capabilities.get("gpu_name") or "GPU CUDA"
        checks.append(_check("cuda", "ok", f"CUDA disponível em {gpu}."))
    else:
        checks.append(_check("cuda", "info", "CUDA não está disponível; o processamento usará CPU quando suportado."))

    if capabilities.get("hf_access_present"):
        checks.append(_check("hf_access", "ok", "Acesso do Hugging Face configurado para recursos que o exigem."))
    else:
        checks.append(
            _check(
                "hf_access",
                "warning",
                "Acesso do Hugging Face não configurado; diarização pode ficar indisponível.",
                "Configure HF_TOKEN apenas no ambiente do speech worker quando precisar de diarização protegida.",
            )
        )

    if capabilities.get("stt_ready"):
        checks.append(_check("stt", "ok", "Runtime STT pronto."))
    else:
        missing = []
        if not capabilities.get("ffmpeg_available"):
            missing.append("FFmpeg")
        if not capabilities.get("whisperx_available"):
            missing.append("WhisperX")
        if not capabilities.get("torch_available"):
            missing.append("Torch")
        reason = "Runtime STT incompleto"
        if missing:
            reason += ": " + ", ".join(missing)
        checks.append(_check("stt", "error", reason + ".", "Instale ou configure os componentes STT indicados."))

    for engine in capabilities.get("tts_engines") or []:
        if isinstance(engine, str):
            engine = {"id": engine, "available": True, "reason": None}
        if not isinstance(engine, dict) or not engine.get("id"):
            continue
        engine_id = str(engine["id"])
        available = bool(engine.get("available"))
        checks.append(
            _check(
                f"tts:{engine_id}",
                "ok" if available else "warning",
                "Motor disponível." if available else str(engine.get("reason") or "Motor TTS indisponível."),
                None if available else "Instale os componentes/modelos exigidos pelo motor e reinicie o speech worker.",
            )
        )

    severity = {"ok": 0, "info": 0, "warning": 1, "error": 2}
    overall = "ok"
    if any(severity.get(check["status"], 0) == 2 for check in checks):
        overall = "error"
    elif any(severity.get(check["status"], 0) == 1 for check in checks):
        overall = "warning"

    return {"status": overall, "checks": checks}
