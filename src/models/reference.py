from sqlalchemy import Column, BigInteger, Text, Integer, Float, DateTime, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.db.session import Base

class ReferenceSource(Base):
    __tablename__ = "reference_sources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_type = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    external_id = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    channel_title = Column(Text, nullable=True)
    channel_id = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(BigInteger, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default="new")
    notes = Column(Text, nullable=True)
    raw_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    import_jobs = relationship("ReferenceImportJob", back_populates="reference_source", cascade="all, delete-orphan")
    transcripts = relationship("Transcript", back_populates="reference_source", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("source_type IN ('youtube_video', 'manual')", name="check_reference_sources_source_type"),
        CheckConstraint("status IN ('new', 'importing', 'transcribed', 'needs_audio_transcription', 'failed', 'archived')", name="check_reference_sources_status"),
        UniqueConstraint("source_type", "external_id", name="unique_reference_sources_source_type_external_id"),
        Index("idx_reference_sources_source_type", source_type),
        Index("idx_reference_sources_external_id", external_id),
        Index("idx_reference_sources_status", status),
        Index("idx_reference_sources_channel_title", channel_title),
        Index("idx_reference_sources_created_at_desc", created_at.desc()),
    )

class ReferenceImportJob(Base):
    __tablename__ = "reference_import_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    reference_source_id = Column(BigInteger, ForeignKey("reference_sources.id", ondelete="CASCADE"), nullable=True)
    source_url = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="queued")
    method = Column(Text, nullable=False, server_default="yt_dlp_captions")
    preferred_languages = Column(JSONB, nullable=True, server_default='["pt", "pt-BR", "en"]')
    selected_language = Column(Text, nullable=True)
    selected_caption_type = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    raw_result_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reference_source = relationship("ReferenceSource", back_populates="import_jobs")
    transcripts = relationship("Transcript", back_populates="import_job")

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'needs_audio_transcription')", name="check_reference_import_jobs_status"),
        CheckConstraint("method IN ('yt_dlp_metadata', 'yt_dlp_captions', 'manual', 'audio_to_text_future')", name="check_reference_import_jobs_method"),
        Index("idx_reference_import_jobs_reference_source_id", reference_source_id),
        Index("idx_reference_import_jobs_status", status),
        Index("idx_reference_import_jobs_created_at_desc", created_at.desc()),
    )

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    reference_source_id = Column(BigInteger, ForeignKey("reference_sources.id", ondelete="CASCADE"), nullable=False)
    import_job_id = Column(BigInteger, ForeignKey("reference_import_jobs.id", ondelete="SET NULL"), nullable=True)
    language = Column(Text, nullable=True)
    source_method = Column(Text, nullable=False)
    full_text = Column(Text, nullable=False)
    full_text_hash = Column(Text, nullable=False)
    srt_text = Column(Text, nullable=True)
    vtt_text = Column(Text, nullable=True)
    raw_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    reference_source = relationship("ReferenceSource", back_populates="transcripts")
    import_job = relationship("ReferenceImportJob", back_populates="transcripts")
    segments = relationship("TranscriptSegment", back_populates="transcript", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("source_method IN ('manual_caption', 'auto_caption', 'manual', 'audio_to_text_future')", name="check_transcripts_source_method"),
        UniqueConstraint("reference_source_id", "full_text_hash", name="unique_transcripts_reference_source_id_full_text_hash"),
        Index("idx_transcripts_reference_source_id", reference_source_id),
    )

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transcript_id = Column(BigInteger, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False)
    segment_index = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    speaker = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    tokens_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    transcript = relationship("Transcript", back_populates="segments")

    __table_args__ = (
        Index("idx_transcript_segments_transcript_id", transcript_id),
        Index("idx_transcript_segments_segment_index", segment_index),
        Index("idx_transcript_segments_start_time", start_time),
        Index("idx_transcript_segments_composite", transcript_id, segment_index),
    )
