from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.speech import SpeechArtifact, SpeechJob
from src.schemas.references import TranscriptCreate, TranscriptSegmentCreate
from src.services.references_service import ReferencesService
from src.services.speech_storage import SpeechStorage


class SpeechResultImportError(RuntimeError):
    pass


class SpeechResultImporter:
    def __init__(self, db: Session, storage: SpeechStorage | None = None) -> None:
        self.db = db
        self.storage = storage or SpeechStorage(os.getenv("SPEECH_DATA_ROOT", "data/speech"))

    def finalize_stt(self, job: SpeechJob, result: dict) -> int | None:
        if result.get("kind") != "stt":
            raise SpeechResultImportError("Resultado não é STT")
        normalized = result.get("normalized")
        if not isinstance(normalized, dict):
            raise SpeechResultImportError("Resultado STT não possui payload normalizado")
        full_text = str(normalized.get("full_text") or "").strip()
        if not full_text:
            raise SpeechResultImportError("Transcrição STT vazia")

        self._persist_artifacts(job.id, result.get("artifacts") or [])

        if job.reference_source_id is None:
            return None
        if job.transcript_id is not None:
            return int(job.transcript_id)

        segments = []
        for index, segment in enumerate(normalized.get("segments") or []):
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            words = segment.get("words") or []
            segments.append(
                TranscriptSegmentCreate(
                    segment_index=index,
                    start_time=segment.get("start"),
                    end_time=segment.get("end"),
                    speaker=segment.get("speaker"),
                    text=text,
                    tokens_json={"words": words} if words else None,
                )
            )

        srt_text = self._artifact_text(job.id, result.get("artifacts") or [], "srt")
        vtt_text = self._artifact_text(job.id, result.get("artifacts") or [], "vtt")
        payload = TranscriptCreate(
            language=normalized.get("language"),
            source_method="whisperx",
            full_text=full_text,
            srt_text=srt_text,
            vtt_text=vtt_text,
            raw_json={
                "engine": normalized.get("engine", "whisperx"),
                "model": normalized.get("model"),
                "diarized": bool(normalized.get("diarized")),
                "alignment_used": bool(normalized.get("alignment_used")),
                "warnings": list(normalized.get("warnings") or []),
                "raw_metadata": normalized.get("raw_metadata") or {},
                "speech_job_id": job.id,
            },
            segments=segments,
        )
        transcript = ReferencesService(self.db).create_manual_transcript(
            int(job.reference_source_id),
            payload,
            job_id=None,
        )
        job.transcript_id = transcript.id
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return int(transcript.id)

    def _persist_artifacts(self, job_id: int, artifacts: list[dict]) -> None:
        for artifact in artifacts:
            storage_key = str(artifact.get("storage_key") or "").strip()
            if not storage_key:
                continue
            existing = self.db.execute(
                select(SpeechArtifact).where(
                    SpeechArtifact.speech_job_id == job_id,
                    SpeechArtifact.storage_key == storage_key,
                )
            ).scalar_one_or_none()
            if existing is not None:
                continue
            self.db.add(
                SpeechArtifact(
                    speech_job_id=job_id,
                    artifact_type=str(artifact.get("artifact_type") or "file"),
                    storage_key=storage_key,
                    filename=str(artifact.get("filename") or Path(storage_key).name),
                    mime_type=artifact.get("mime_type"),
                    size_bytes=artifact.get("size_bytes"),
                )
            )
        self.db.commit()

    def _artifact_text(self, job_id: int, artifacts: list[dict], artifact_type: str) -> str | None:
        for artifact in artifacts:
            if artifact.get("artifact_type") != artifact_type:
                continue
            storage_key = str(artifact.get("storage_key") or "")
            path = (self.storage.root / storage_key).resolve()
            self.storage.safe_storage_key(path)
            expected_root = self.storage.artifacts_dir(job_id).resolve()
            try:
                path.relative_to(expected_root)
            except ValueError as exc:
                raise SpeechResultImportError("Artefato aponta para fora do diretório do job") from exc
            if path.is_file():
                return path.read_text(encoding="utf-8")
        return None
