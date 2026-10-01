from __future__ import annotations

import argparse
import sys
from pathlib import Path

import src.db.base  # noqa: F401  # register all SQLAlchemy models
from src.db.session import SessionLocal
from src.repositories.speech_jobs import SpeechJobRepository
from src.schemas.speech_jobs import SpeechSttJobCreate
from src.services.speech_jobs_service import SpeechJobsService
from speech_worker.runtime.capabilities import detect_capabilities
from speech_worker.runtime.executor import SpeechExecutor
from speech_worker.worker import run_once


def _chunks(path: Path, chunk_size: int = 1024 * 1024):
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            yield chunk


def main() -> int:
    parser = argparse.ArgumentParser(description="Real Speech Suite STT smoke test.")
    parser.add_argument("input", help="Small audio/video file to transcribe")
    parser.add_argument("--preset", default="fast")
    parser.add_argument("--language", default="pt")
    parser.add_argument("--diarization", action="store_true")
    args = parser.parse_args()

    source = Path(args.input).expanduser().resolve()
    if not source.is_file():
        print(f"FAIL: arquivo de entrada não existe: {source}")
        return 1

    capabilities = detect_capabilities("speech-stt-smoke")
    if not capabilities.stt_ready:
        print(
            "SKIP: runtime STT indisponível "
            f"(ffmpeg={capabilities.ffmpeg_available}, "
            f"whisperx={capabilities.whisperx_available}, torch={capabilities.torch_available})"
        )
        return 2
    if args.diarization and not capabilities.diarization_ready:
        print("SKIP: diarização pedida, mas HF access/runtime de diarização não está pronto")
        return 2

    db = SessionLocal()
    try:
        service = SpeechJobsService(db)
        request = SpeechSttJobCreate(
            preset=args.preset,
            language=args.language,
            diarization=args.diarization,
            export_formats=["txt", "json", "srt", "vtt"],
        )
        job = service.create_uploaded_stt_job(
            request,
            filename=source.name,
            chunks=_chunks(source),
        )
        repo = SpeechJobRepository(db)
        worked = run_once(repo, SpeechExecutor(), "speech-stt-smoke", 600)
        if not worked:
            print("FAIL: worker não reivindicou o job STT criado")
            return 1

        db.expire_all()
        completed = repo.get(job.id)
        if completed is None:
            print("FAIL: job STT desapareceu após execução")
            return 1
        if completed.status != "completed":
            print(f"FAIL: job STT terminou como {completed.status}: {completed.error_code} {completed.error_message}")
            return 1

        result = completed.result_json or {}
        normalized = result.get("normalized") or {}
        if not str(normalized.get("full_text") or "").strip():
            print("FAIL: job STT completou sem texto normalizado")
            return 1

        artifacts = repo.list_artifacts(job.id)
        artifact_types = {item.artifact_type for item in artifacts}
        expected = {"txt", "json", "srt", "vtt"}
        if not expected.issubset(artifact_types):
            print(f"FAIL: artefatos STT ausentes: {sorted(expected - artifact_types)}")
            return 1
        for artifact in artifacts:
            _, path = service.resolve_artifact_download(job.id, artifact.id)
            if path.stat().st_size <= 0:
                print(f"FAIL: artefato vazio: {path}")
                return 1

        print(
            f"PASS: STT job={job.id} chars={len(normalized['full_text'])} "
            f"artifacts={len(artifacts)} transcript_id={completed.transcript_id}"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
