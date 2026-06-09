from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
import hashlib
from fastapi import BackgroundTasks

from src.models.reference import ReferenceSource, ReferenceImportJob, Transcript, TranscriptSegment
from src.schemas.references import (
    ReferenceSourceCreate,
    ReferenceSourceUpdate,
    ReferenceImportJobRead,
    YouTubeUrlImportRequest,
    TranscriptCreate,
    TranscriptSegmentCreate
)
from src.repositories.references_repository import ReferencesRepository
from src.services.youtube_reference_importer import YouTubeReferenceImporter
from src.schemas.references import extract_youtube_video_id

class ReferencesService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ReferencesRepository(db)

    def import_youtube_url(self, request: YouTubeUrlImportRequest, background_tasks: BackgroundTasks) -> ReferenceImportJob:
        """
        Validates the YouTube URL, creates a queued import job, and enqueues the BackgroundTask.
        """
        # Create a queued import job (reference_source_id is initially None)
        job = self.repo.create_import_job(
            source_url=request.url,
            preferred_languages=request.preferred_languages,
            method="yt_dlp_captions"
        )

        # Enqueue the background task with only the job ID
        background_tasks.add_task(
            execute_import_job_task,
            job_id=job.id,
            preferred_languages=request.preferred_languages,
            allow_auto_captions=request.allow_auto_captions
        )

        return job

    def list_reference_sources(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        channel_title: Optional[str] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc"
    ) -> Tuple[List[ReferenceSource], int]:
        return self.repo.list_reference_sources(
            limit=limit,
            offset=offset,
            search=search,
            source_type=source_type,
            status=status,
            channel_title=channel_title,
            sort_by=sort_by,
            sort_order=sort_order
        )

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
        """
        Creates a manual transcript, computing its normalized SHA-256 hash.
        If a duplicate is found, rolls back and returns the existing one.
        """
        normalized_text = " ".join(payload.full_text.split())
        full_text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

        # Check existing transcript to avoid duplicate attempts
        existing = self.repo.get_transcript_by_source_and_hash(source_id, full_text_hash)
        if existing:
            return existing

        try:
            db_transcript = self.repo.create_transcript(
                reference_source_id=source_id,
                import_job_id=job_id,
                language=payload.language,
                source_method=payload.source_method,
                full_text=payload.full_text,
                full_text_hash=full_text_hash,
                srt_text=payload.srt_text,
                vtt_text=payload.vtt_text,
                raw_json=payload.raw_json
            )

            if payload.segments:
                self.repo.create_transcript_segments(db_transcript.id, payload.segments)

            # Update the reference source status to transcribed
            source = self.repo.get_reference_source_by_id(source_id)
            if source:
                source.status = "transcribed"
                source.updated_at = datetime.now(timezone.utc)
                self.db.add(source)
                self.db.commit()

            return db_transcript

        except IntegrityError:
            self.db.rollback()
            # Retrieve existing transcript from race condition
            existing = self.repo.get_transcript_by_source_and_hash(source_id, full_text_hash)
            if not existing:
                raise ValueError("Concorrência ao criar transcrição.")
            return existing


# Module-level background task executor using an isolated session
def execute_import_job_task(job_id: int, preferred_languages: List[str], allow_auto_captions: bool):
    from src.db.session import SessionLocal
    db = SessionLocal()
    try:
        repo = ReferencesRepository(db)
        importer = YouTubeReferenceImporter()

        job = repo.get_import_job_by_id(job_id)
        if not job:
            return

        # 1. Update job to running
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        repo.save_import_job(job)

        # 2. Extract metadata
        try:
            info = importer.extract_metadata(job.source_url)
            external_id = info.get("id")
            if not external_id:
                raise ValueError("Identificador do YouTube (id) ausente na metadata extraída.")
        except Exception as e:
            # General metadata extraction failure
            job.status = "failed"
            job.error_message = f"Falha ao extrair metadados do YouTube: {str(e)}"
            job.finished_at = datetime.now(timezone.utc)
            repo.save_import_job(job)
            return

        # 3. Clean and parse metadata
        raw_json = importer.clean_metadata(info)
        title = info.get("title", "Untitled YouTube Video")
        channel_title = info.get("channel", info.get("uploader"))
        channel_id = info.get("channel_id", info.get("uploader_id"))
        description = info.get("description")
        duration_seconds = info.get("duration")
        view_count = info.get("view_count")
        like_count = info.get("like_count")
        thumbnail_url = info.get("thumbnail")
        language = info.get("language")

        published_at = None
        upload_date = info.get("upload_date")
        if upload_date:
            try:
                published_at = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        # 4. Resolve or create ReferenceSource (Concurrency protection)
        source = repo.get_reference_source_by_external_id("youtube_video", external_id)
        if source:
            # Update existing source
            source.source_url = job.source_url
            source.title = title
            source.channel_title = channel_title
            source.channel_id = channel_id
            source.description = description
            source.published_at = published_at
            source.duration_seconds = duration_seconds
            source.view_count = view_count
            source.like_count = like_count
            source.thumbnail_url = thumbnail_url
            source.language = language
            source.raw_json = raw_json
            source.status = "importing"
            source.updated_at = datetime.now(timezone.utc)
            db.add(source)
            db.commit()
            db.refresh(source)
        else:
            # Insert a new source
            source_in = ReferenceSourceCreate(
                source_type="youtube_video",
                source_url=job.source_url,
                external_id=external_id,
                title=title,
                channel_title=channel_title,
                channel_id=channel_id,
                description=description,
                published_at=published_at,
                duration_seconds=duration_seconds,
                view_count=view_count,
                like_count=like_count,
                thumbnail_url=thumbnail_url,
                language=language,
                status="importing",
                raw_json=raw_json
            )
            
            try:
                source = ReferenceSource(**source_in.model_dump())
                db.add(source)
                db.commit()
                db.refresh(source)
            except IntegrityError:
                db.rollback()
                # Fetch source created by concurrent request
                source = repo.get_reference_source_by_external_id("youtube_video", external_id)
                if not source:
                    raise ValueError("Concorrência catastrófica ao criar fonte de referência.")
                
                # Update it
                source.source_url = job.source_url
                source.title = title
                source.channel_title = channel_title
                source.channel_id = channel_id
                source.description = description
                source.published_at = published_at
                source.duration_seconds = duration_seconds
                source.view_count = view_count
                source.like_count = like_count
                source.thumbnail_url = thumbnail_url
                source.language = language
                source.raw_json = raw_json
                source.status = "importing"
                source.updated_at = datetime.now(timezone.utc)
                db.add(source)
                db.commit()
                db.refresh(source)

        # Link job to source
        job.reference_source_id = source.id
        repo.save_import_job(job)

        # 5. Process captions / subtitles
        caption_track = importer.select_caption_track(info, preferred_languages, allow_auto_captions)
        
        if caption_track:
            selected_lang, caption_type, caption_url = caption_track
            
            try:
                # Download and parse captions
                vtt_text = importer.fetch_caption_text(caption_url)
                parsed_segments = importer.parse_vtt(vtt_text)
                
                if not parsed_segments:
                    raise ValueError("Nenhum segmento textual pôde ser extraído do arquivo de legenda VTT.")
                    
                full_text = importer.build_clean_full_text(parsed_segments)
                normalized_text = " ".join(full_text.split())
                full_text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()

                # Check if this exact transcript is already registered
                existing_transcript = repo.get_transcript_by_source_and_hash(source.id, full_text_hash)
                
                if existing_transcript:
                    # Reuse the existing transcript
                    job.selected_language = selected_lang
                    job.selected_caption_type = caption_type
                    job.status = "completed"
                    job.raw_result_json = {
                        "selected_language": selected_lang,
                        "selected_caption_type": caption_type,
                        "caption_ext": "vtt",
                        "caption_track_url": caption_url,
                        "transcript_reused": True,
                        "transcript_id": existing_transcript.id
                    }
                else:
                    # Insert a new transcript
                    source_method = "manual_caption" if caption_type == "manual_caption" else "auto_caption"
                    db_transcript = repo.create_transcript(
                        reference_source_id=source.id,
                        import_job_id=job.id,
                        language=selected_lang,
                        source_method=source_method,
                        full_text=full_text,
                        full_text_hash=full_text_hash,
                        vtt_text=vtt_text,
                        raw_json={"parsed_metadata": {"char_count": len(full_text), "segment_count": len(parsed_segments)}}
                    )
                    
                    # Convert segments
                    db_segments_in = [
                        TranscriptSegmentCreate(
                            segment_index=seg["segment_index"],
                            start_time=seg["start_time"],
                            end_time=seg["end_time"],
                            text=seg["text"]
                        )
                        for seg in parsed_segments
                    ]
                    repo.create_transcript_segments(db_transcript.id, db_segments_in)

                    job.selected_language = selected_lang
                    job.selected_caption_type = caption_type
                    job.status = "completed"
                    job.raw_result_json = {
                        "selected_language": selected_lang,
                        "selected_caption_type": caption_type,
                        "caption_ext": "vtt",
                        "caption_track_url": caption_url,
                        "transcript_reused": False,
                        "transcript_id": db_transcript.id
                    }

                source.status = "transcribed"
                
            except Exception as caption_err:
                # Caption download or parsing failed: treat as partial failure / needs_audio_transcription
                job.status = "needs_audio_transcription"
                job.error_message = f"Falha ao processar legendas ({caption_type}): {str(caption_err)}"
                job.raw_result_json = {
                    "selected_language": selected_lang,
                    "selected_caption_type": caption_type,
                    "caption_track_url": caption_url,
                    "error": str(caption_err)
                }
                source.status = "needs_audio_transcription"

        else:
            # No captions available at all
            job.status = "needs_audio_transcription"
            job.error_message = "Vídeo não possui legendas manuais ou automáticas nos idiomas preferidos."
            job.raw_result_json = {
                "subtitles_languages": raw_json.get("subtitles_languages", []),
                "automatic_captions_languages": raw_json.get("automatic_captions_languages", [])
            }
            source.status = "needs_audio_transcription"

        # Save updates
        job.finished_at = datetime.now(timezone.utc)
        repo.save_import_job(job)

        source.updated_at = datetime.now(timezone.utc)
        db.add(source)
        db.commit()

    except Exception as general_err:
        # Fallback for unexpected task crashes
        if 'job' in locals() and job:
            job.status = "failed"
            job.error_message = f"Erro geral interno no processamento do job: {str(general_err)}"
            job.finished_at = datetime.now(timezone.utc)
            db.add(job)
            db.commit()
    finally:
        db.close()
