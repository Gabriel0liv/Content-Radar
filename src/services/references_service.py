from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Tuple
from datetime import datetime, timezone
import hashlib
from fastapi import BackgroundTasks

from src.models.reference import ReferenceSource, ReferenceImportJob, Transcript, TranscriptSegment
from src.schemas.references import (
    ReferenceSourceCreate,
    ReferenceSourceUpdate,
    YouTubeUrlImportRequest,
    TranscriptCreate,
    TranscriptSegmentCreate,
    extract_youtube_video_id,
)
from src.repositories.references_repository import ReferencesRepository
from src.services.youtube_reference_importer import YouTubeReferenceImporter
from src.services.transcript_topic_enrichment import enrich_topics_from_transcript


class ReferencesService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReferencesRepository(db)

    def import_youtube_url(self, request: YouTubeUrlImportRequest, background_tasks: BackgroundTasks) -> ReferenceImportJob:
        video_id = extract_youtube_video_id(request.url)
        existing_source = self.repo.get_reference_source_by_youtube_video_id(video_id)
        job = self.repo.create_import_job(source_url=request.url, preferred_languages=request.preferred_languages, method="yt_dlp_captions")

        if existing_source:
            job.reference_source_id = existing_source.id
            active_transcript = next((t for t in existing_source.transcripts if t.is_active), None)
            if active_transcript:
                job.status = "completed"
                job.finished_at = datetime.now(timezone.utc)
                job.selected_language = active_transcript.language
                job.selected_caption_type = "existing_transcript"
                job.raw_result_json = {
                    "deduplicated": True,
                    "youtube_video_id": video_id,
                    "reused_reference_source_id": existing_source.id,
                    "reused_transcript_id": active_transcript.id,
                }
                return self.repo.save_import_job(job)
            self.repo.save_import_job(job)

        background_tasks.add_task(
            execute_import_job_task,
            job_id=job.id,
            preferred_languages=request.preferred_languages,
            allow_auto_captions=request.allow_auto_captions,
            transcription_mode=request.transcription_mode,
        )
        return job

    def list_reference_sources(self, limit: int = 50, offset: int = 0, search: Optional[str] = None, source_type: Optional[str] = None, status: Optional[str] = None, channel_title: Optional[str] = None, sort_by: Optional[str] = "created_at", sort_order: Optional[str] = "desc") -> Tuple[List[ReferenceSource], int]:
        return self.repo.list_reference_sources(limit=limit, offset=offset, search=search, source_type=source_type, status=status, channel_title=channel_title, sort_by=sort_by, sort_order=sort_order)

    def get_reference_source(self, source_id: int) -> Optional[ReferenceSource]:
        return self.repo.get_reference_source_by_id(source_id)

    def update_reference_source(self, source_id: int, source_in: ReferenceSourceUpdate) -> Optional[ReferenceSource]:
        return self.repo.update_reference_source(source_id, source_in)

    def get_import_job(self, job_id: int) -> Optional[ReferenceImportJob]:
        return self.repo.get_import_job_by_id(job_id)

    def get_import_jobs_for_source(self, source_id: int) -> List[ReferenceImportJob]:
        return self.repo.list_import_jobs_by_source_id(source_id)

    def get_transcripts_for_source(self, source_id: int) -> List[Transcript]:
        return self.repo.list_transcripts_by_source(source_id)

    def get_transcript(self, transcript_id: int) -> Optional[Transcript]:
        return self.repo.get_transcript_by_id(transcript_id)

    def get_transcript_segments(self, transcript_id: int) -> List[TranscriptSegment]:
        return self.repo.list_segments_by_transcript_id(transcript_id)

    def create_manual_transcript(self, source_id: int, payload: TranscriptCreate, job_id: Optional[int] = None) -> Transcript:
        normalized_text = " ".join(payload.full_text.split())
        full_text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        existing = self.repo.get_transcript_by_source_and_hash(source_id, full_text_hash)
        duplicate_of_id = existing.id if existing else None
        version_number = self.repo.get_next_transcript_version_number(source_id)
        try:
            self.repo.deactivate_transcripts_for_source(source_id)
            db_transcript = self.repo.create_transcript_version(
                reference_source_id=source_id,
                import_job_id=job_id,
                language=payload.language,
                source_method=payload.source_method,
                full_text=payload.full_text,
                full_text_hash=full_text_hash,
                version_number=version_number,
                is_active=True,
                duplicate_of_transcript_id=duplicate_of_id,
                srt_text=payload.srt_text,
                vtt_text=payload.vtt_text,
                raw_json=payload.raw_json,
            )
            if payload.segments:
                self.repo.create_transcript_segments(db_transcript.id, payload.segments)
            source = self.repo.get_reference_source_by_id(source_id)
            if source:
                source.status = "transcribed"
                source.updated_at = datetime.now(timezone.utc)
                self.db.add(source)
                self.db.commit()
                if source.youtube_video_id:
                    try:
                        enrich_topics_from_transcript(self.db, source.youtube_video_id, db_transcript.full_text)
                    except Exception:
                        pass
            return db_transcript
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Erro ao salvar versão da transcrição manual.")


def _save_transcript(repo, source, job, language, source_method, full_text, segments, raw_json=None, vtt_text=None):
    normalized_text = " ".join(full_text.split())
    full_text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    existing = repo.get_transcript_by_source_and_hash(source.id, full_text_hash)
    version_number = repo.get_next_transcript_version_number(source.id)
    repo.deactivate_transcripts_for_source(source.id)
    transcript = repo.create_transcript_version(
        reference_source_id=source.id,
        import_job_id=job.id,
        language=language,
        source_method=source_method,
        full_text=full_text,
        full_text_hash=full_text_hash,
        version_number=version_number,
        is_active=True,
        duplicate_of_transcript_id=existing.id if existing else None,
        vtt_text=vtt_text,
        raw_json=raw_json,
    )
    repo.create_transcript_segments(
        transcript.id,
        [
            TranscriptSegmentCreate(
                segment_index=seg["segment_index"],
                start_time=seg.get("start_time"),
                end_time=seg.get("end_time"),
                text=seg["text"],
            )
            for seg in segments
        ],
    )
    if source.youtube_video_id:
        try:
            enrich_topics_from_transcript(repo.db, source.youtube_video_id, transcript.full_text)
        except Exception:
            pass
    return transcript, version_number, full_text_hash, existing


def _transcribe_from_audio(repo, importer, source, job):
    audio = importer.transcribe_audio_from_youtube(job.source_url)
    transcript, version_number, full_text_hash, existing = _save_transcript(
        repo=repo,
        source=source,
        job=job,
        language=audio.get("language"),
        source_method="audio_to_text_future",
        full_text=audio["full_text"],
        segments=audio["segments"],
        raw_json={
            "engine": "faster-whisper",
            "model": audio.get("model"),
            "language_probability": audio.get("language_probability"),
            "char_count": len(audio["full_text"]),
            "segment_count": len(audio["segments"]),
            "literal_text": True,
        },
    )
    job.method = "audio_to_text_future"
    job.selected_language = audio.get("language")
    job.selected_caption_type = "audio_to_text"
    job.status = "completed"
    job.error_message = None
    job.raw_result_json = {
        "transcription_mode_used": "audio",
        "transcript_id": transcript.id,
        "version_number": version_number,
        "full_text_hash": full_text_hash,
        "duplicate_of_transcript_id": existing.id if existing else None,
        "engine": "faster-whisper",
        "model": audio.get("model"),
    }
    source.status = "transcribed"
    return transcript


def execute_import_job_task(job_id: int, preferred_languages: List[str], allow_auto_captions: bool, transcription_mode: str = "auto"):
    from src.db.session import SessionLocal

    db = SessionLocal()
    job = None
    try:
        repo = ReferencesRepository(db)
        importer = YouTubeReferenceImporter()
        job = repo.get_import_job_by_id(job_id)
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        repo.save_import_job(job)

        canonical_video_id = extract_youtube_video_id(job.source_url)
        preexisting_source = repo.get_reference_source_by_youtube_video_id(canonical_video_id)

        try:
            info = importer.extract_metadata(job.source_url)
            external_id = info.get("id") or canonical_video_id
            if not external_id:
                raise ValueError("Identificador do YouTube ausente.")
        except Exception as exc:
            job.status = "failed"
            job.error_message = f"Falha ao extrair metadados do YouTube: {exc}"
            job.finished_at = datetime.now(timezone.utc)
            repo.save_import_job(job)
            return

        raw_json = importer.clean_metadata(info)
        published_at = None
        upload_date = info.get("upload_date")
        if upload_date:
            try:
                published_at = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        values = dict(
            source_url=job.source_url,
            youtube_video_id=canonical_video_id,
            title=info.get("title", "Untitled YouTube Video"),
            channel_title=info.get("channel", info.get("uploader")),
            channel_id=info.get("channel_id", info.get("uploader_id")),
            description=info.get("description"),
            published_at=published_at,
            duration_seconds=info.get("duration"),
            view_count=info.get("view_count"),
            like_count=info.get("like_count"),
            thumbnail_url=info.get("thumbnail"),
            language=info.get("language"),
            raw_json=raw_json,
        )

        source = preexisting_source or repo.get_reference_source_by_youtube_video_id(canonical_video_id) or repo.get_reference_source_by_external_id("youtube_video", external_id)
        if source:
            for key, value in values.items():
                setattr(source, key, value)
            source.external_id = external_id
            source.status = "importing"
            source.updated_at = datetime.now(timezone.utc)
            db.add(source)
            db.commit()
            db.refresh(source)
        else:
            source_in = ReferenceSourceCreate(
                source_type="youtube_video",
                external_id=external_id,
                youtube_video_id=canonical_video_id,
                status="importing",
                **{k: v for k, v in values.items() if k != "youtube_video_id"},
            )
            try:
                source = ReferenceSource(**source_in.model_dump())
                db.add(source)
                db.commit()
                db.refresh(source)
            except IntegrityError:
                db.rollback()
                source = repo.get_reference_source_by_youtube_video_id(canonical_video_id) or repo.get_reference_source_by_external_id("youtube_video", external_id)
                if not source:
                    raise

        job.reference_source_id = source.id
        repo.save_import_job(job)
        caption_track = importer.select_caption_track(info, preferred_languages, allow_auto_captions)

        if transcription_mode == "max_fidelity":
            try:
                _transcribe_from_audio(repo, importer, source, job)
            except Exception as audio_exc:
                if not caption_track:
                    raise RuntimeError(f"Falha na transcrição de áudio: {audio_exc}") from audio_exc
                job.error_message = f"Áudio falhou; usando legenda do YouTube: {audio_exc}"
            else:
                job.finished_at = datetime.now(timezone.utc)
                repo.save_import_job(job)
                source.updated_at = datetime.now(timezone.utc)
                db.add(source)
                db.commit()
                return

        if caption_track:
            selected_lang, caption_type, caption_url = caption_track
            try:
                vtt_text = importer.fetch_caption_text(caption_url)
                segments = importer.parse_vtt(vtt_text)
                if not segments:
                    raise ValueError("Nenhum segmento textual extraído do VTT.")
                full_text = importer.build_clean_full_text(segments)
                transcript, version_number, full_text_hash, existing = _save_transcript(
                    repo=repo,
                    source=source,
                    job=job,
                    language=selected_lang,
                    source_method="manual_caption" if caption_type == "manual_caption" else "auto_caption",
                    full_text=full_text,
                    segments=segments,
                    raw_json={
                        "char_count": len(full_text),
                        "segment_count": len(segments),
                        "deduplication": "time-overlap-only",
                    },
                    vtt_text=vtt_text,
                )
                job.selected_language = selected_lang
                job.selected_caption_type = caption_type
                job.status = "completed"
                job.raw_result_json = {
                    "transcription_mode_used": "youtube_caption",
                    "selected_language": selected_lang,
                    "selected_caption_type": caption_type,
                    "transcript_id": transcript.id,
                    "version_number": version_number,
                    "full_text_hash": full_text_hash,
                    "duplicate_of_transcript_id": existing.id if existing else None,
                }
                source.status = "transcribed"
            except Exception as caption_exc:
                try:
                    _transcribe_from_audio(repo, importer, source, job)
                    job.raw_result_json["caption_fallback_reason"] = str(caption_exc)
                except Exception as audio_exc:
                    job.status = "needs_audio_transcription"
                    job.error_message = f"Legenda falhou ({caption_exc}); áudio falhou ({audio_exc})"
                    source.status = "needs_audio_transcription"
        else:
            try:
                _transcribe_from_audio(repo, importer, source, job)
            except Exception as audio_exc:
                job.status = "needs_audio_transcription"
                job.error_message = f"Sem legendas e falha na transcrição de áudio: {audio_exc}"
                job.raw_result_json = {
                    "subtitles_languages": raw_json.get("subtitles_languages", []),
                    "automatic_captions_languages": raw_json.get("automatic_captions_languages", []),
                    "audio_error": str(audio_exc),
                }
                source.status = "needs_audio_transcription"

        job.finished_at = datetime.now(timezone.utc)
        repo.save_import_job(job)
        source.updated_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()
    except Exception as general_err:
        if job:
            job.status = "failed"
            job.error_message = f"Erro geral interno no processamento do job: {general_err}"
            job.finished_at = datetime.now(timezone.utc)
            db.add(job)
            db.commit()
    finally:
        db.close()
