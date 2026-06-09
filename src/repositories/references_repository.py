from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
import json

from src.models.reference import ReferenceSource, ReferenceImportJob, Transcript, TranscriptSegment
from src.schemas.references import ReferenceSourceCreate, ReferenceSourceUpdate, TranscriptCreate, TranscriptSegmentCreate

class ReferencesRepository:
    def __init__(self, db: Session):
        self.db = db

    # ReferenceSource CRUD
    def create_reference_source(self, source_in: ReferenceSourceCreate) -> ReferenceSource:
        source_data = source_in.model_dump()
        db_source = ReferenceSource(**source_data)
        self.db.add(db_source)
        self.db.commit()
        self.db.refresh(db_source)
        return db_source

    def update_reference_source(self, source_id: int, source_in: ReferenceSourceUpdate) -> Optional[ReferenceSource]:
        db_source = self.get_reference_source_by_id(source_id)
        if not db_source:
            return None
        
        update_data = source_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_source, key, value)
            
        db_source.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(db_source)
        return db_source

    def get_reference_source_by_id(self, source_id: int) -> Optional[ReferenceSource]:
        return self.db.query(ReferenceSource).filter(ReferenceSource.id == source_id).first()

    def get_reference_source_by_external_id(self, source_type: str, external_id: str) -> Optional[ReferenceSource]:
        return self.db.query(ReferenceSource).filter(
            ReferenceSource.source_type == source_type,
            ReferenceSource.external_id == external_id
        ).first()

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
        query = self.db.query(ReferenceSource)
        
        if source_type and source_type != "Todos":
            query = query.filter(ReferenceSource.source_type == source_type)
        if status and status != "Todos":
            query = query.filter(ReferenceSource.status == status)
        if channel_title:
            query = query.filter(ReferenceSource.channel_title.ilike(f"%{channel_title}%"))
            
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (ReferenceSource.title.ilike(search_pattern)) |
                (func.coalesce(ReferenceSource.description, '').ilike(search_pattern)) |
                (func.coalesce(ReferenceSource.channel_title, '').ilike(search_pattern))
            )
            
        total = query.count()
        
        sorting_whitelist = {
            "created_at": ReferenceSource.created_at,
            "updated_at": ReferenceSource.updated_at,
            "title": ReferenceSource.title,
            "view_count": ReferenceSource.view_count,
            "like_count": ReferenceSource.like_count,
            "duration_seconds": ReferenceSource.duration_seconds,
            "published_at": ReferenceSource.published_at
        }
        
        sort_column = sorting_whitelist.get(sort_by, ReferenceSource.created_at)
        
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
            
        items = query.offset(offset).limit(limit).all()
        return items, total

    # ReferenceImportJob CRUD
    def create_import_job(self, source_url: str, preferred_languages: List[str], method: str = "yt_dlp_captions") -> ReferenceImportJob:
        db_job = ReferenceImportJob(
            source_url=source_url,
            preferred_languages=preferred_languages,
            method=method,
            status="queued"
        )
        self.db.add(db_job)
        self.db.commit()
        self.db.refresh(db_job)
        return db_job

    def get_import_job_by_id(self, job_id: int) -> Optional[ReferenceImportJob]:
        return self.db.query(ReferenceImportJob).filter(ReferenceImportJob.id == job_id).first()

    def list_import_jobs_by_source_id(self, source_id: int) -> List[ReferenceImportJob]:
        return self.db.query(ReferenceImportJob).filter(
            ReferenceImportJob.reference_source_id == source_id
        ).order_by(ReferenceImportJob.created_at.desc()).all()

    def save_import_job(self, job: ReferenceImportJob) -> ReferenceImportJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    # Transcript CRUD
    def create_transcript(
        self,
        reference_source_id: int,
        import_job_id: Optional[int],
        language: Optional[str],
        source_method: str,
        full_text: str,
        full_text_hash: str,
        srt_text: Optional[str] = None,
        vtt_text: Optional[str] = None,
        raw_json: Optional[Dict[str, Any]] = None
    ) -> Transcript:
        db_transcript = Transcript(
            reference_source_id=reference_source_id,
            import_job_id=import_job_id,
            language=language,
            source_method=source_method,
            full_text=full_text,
            full_text_hash=full_text_hash,
            srt_text=srt_text,
            vtt_text=vtt_text,
            raw_json=raw_json
        )
        self.db.add(db_transcript)
        self.db.commit()
        self.db.refresh(db_transcript)
        return db_transcript

    def create_transcript_segments(self, transcript_id: int, segments_in: List[TranscriptSegmentCreate]) -> List[TranscriptSegment]:
        db_segments = []
        for seg in segments_in:
            seg_data = seg.model_dump()
            seg_data["transcript_id"] = transcript_id
            db_seg = TranscriptSegment(**seg_data)
            self.db.add(db_seg)
            db_segments.append(db_seg)
        self.db.commit()
        return db_segments

    def list_transcripts_by_source(self, source_id: int) -> List[Transcript]:
        return self.db.query(Transcript).filter(
            Transcript.reference_source_id == source_id
        ).order_by(Transcript.created_at.desc()).all()

    def get_transcript_by_id(self, transcript_id: int) -> Optional[Transcript]:
        return self.db.query(Transcript).filter(Transcript.id == transcript_id).first()

    def get_transcript_by_source_and_hash(self, source_id: int, text_hash: str) -> Optional[Transcript]:
        return self.db.query(Transcript).filter(
            Transcript.reference_source_id == source_id,
            Transcript.full_text_hash == text_hash
        ).first()

    def list_segments_by_transcript_id(self, transcript_id: int) -> List[TranscriptSegment]:
        return self.db.query(TranscriptSegment).filter(
            TranscriptSegment.transcript_id == transcript_id
        ).order_by(TranscriptSegment.segment_index.asc()).all()

    def get_next_transcript_version_number(self, reference_source_id: int) -> int:
        max_ver = self.db.query(func.max(Transcript.version_number)).filter(
            Transcript.reference_source_id == reference_source_id
        ).scalar()
        return (max_ver or 0) + 1

    def deactivate_transcripts_for_source(self, reference_source_id: int) -> None:
        self.db.query(Transcript).filter(
            Transcript.reference_source_id == reference_source_id
        ).update({Transcript.is_active: False})
        self.db.commit()

    def create_transcript_version(
        self,
        reference_source_id: int,
        import_job_id: Optional[int],
        language: Optional[str],
        source_method: str,
        full_text: str,
        full_text_hash: str,
        version_number: int,
        is_active: bool,
        duplicate_of_transcript_id: Optional[int] = None,
        srt_text: Optional[str] = None,
        vtt_text: Optional[str] = None,
        raw_json: Optional[Dict[str, Any]] = None
    ) -> Transcript:
        db_transcript = Transcript(
            reference_source_id=reference_source_id,
            import_job_id=import_job_id,
            language=language,
            source_method=source_method,
            full_text=full_text,
            full_text_hash=full_text_hash,
            version_number=version_number,
            is_active=is_active,
            duplicate_of_transcript_id=duplicate_of_transcript_id,
            srt_text=srt_text,
            vtt_text=vtt_text,
            raw_json=raw_json
        )
        self.db.add(db_transcript)
        self.db.commit()
        self.db.refresh(db_transcript)
        return db_transcript
