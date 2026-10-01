from __future__ import annotations

import argparse
import sys

import src.db.base  # noqa: F401  # register all SQLAlchemy models
from src.db.session import SessionLocal
from src.repositories.speech_jobs import SpeechJobRepository
from src.schemas.speech_jobs import SpeechTtsJobCreate
from src.services.speech_jobs_service import SpeechJobsService
from speech_worker.runtime.capabilities import detect_capabilities
from speech_worker.runtime.executor import SpeechExecutor
from speech_worker.worker import run_once


def _engine_state(engine: str) -> dict | None:
    capabilities = detect_capabilities("speech-tts-smoke")
    for item in capabilities.tts_engines:
        if isinstance(item, dict) and item.get("id") == engine:
            return item
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Real Speech Suite TTS smoke test.")
    parser.add_argument("--engine", choices=["kokoro", "piper"], default="kokoro")
    parser.add_argument("--voice", default=None)
    parser.add_argument("--text", default="Olá! Este é um teste curto de síntese de voz em português do Brasil.")
    parser.add_argument("--format", choices=["wav", "mp3"], default="wav", dest="output_format")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    state = _engine_state(args.engine)
    if not state or not state.get("available"):
        reason = (state or {}).get("reason") or "motor não informado pelo worker"
        print(f"SKIP: motor TTS {args.engine!r} indisponível: {reason}")
        return 2

    voice = args.voice or ("pt_br_dora" if args.engine == "kokoro" else "pt_br_faber")
    db = SessionLocal()
    try:
        service = SpeechJobsService(db)
        request = SpeechTtsJobCreate(
            text=args.text,
            engine=args.engine,
            voice=voice,
            output_format=args.output_format,
            preview=args.preview,
            preview_chars=300,
            analyze_ptbr=True,
        )
        job = service.create_tts_job(request)
        repo = SpeechJobRepository(db)
        worked = run_once(repo, SpeechExecutor(), "speech-tts-smoke", 300)
        if not worked:
            print("FAIL: worker não reivindicou o job TTS criado")
            return 1

        db.expire_all()
        completed = repo.get(job.id)
        if completed is None:
            print("FAIL: job TTS desapareceu após execução")
            return 1
        if completed.status != "completed":
            print(f"FAIL: job TTS terminou como {completed.status}: {completed.error_code} {completed.error_message}")
            return 1

        artifacts = repo.list_artifacts(job.id)
        audio = [item for item in artifacts if item.artifact_type == "audio"]
        if not audio:
            print("FAIL: job TTS completou sem artefato de áudio")
            return 1
        for artifact in audio:
            _, path = service.resolve_artifact_download(job.id, artifact.id)
            if path.stat().st_size <= 0:
                print(f"FAIL: artefato vazio: {path}")
                return 1

        print(f"PASS: TTS {args.engine} job={job.id} artifacts={len(audio)}")
        for artifact in audio:
            print(f"  - {artifact.filename} ({artifact.size_bytes or 0} bytes)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
