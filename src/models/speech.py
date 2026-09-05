from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.session import Base


class SpeechJob(Base):
    __tablename__ = "speech_jobs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    operation = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="queued")
    stage = Column(Text, nullable=False, server_default="queued")
    progress_percent = Column(Integer, nullable=False, server_default="0")
    progress_message = Column(Text, nullable=True)
    requested_config_json = Column(JSONB, nullable=False, server_default="{}")
    resolved_config_json = Column(JSONB, nullable=True)
    input_path = Column(Text, nullable=True)
    reference_source_id = Column(BigInteger, ForeignKey("reference_sources.id", ondelete="SET NULL"), nullable=True)
    transcript_id = Column(BigInteger, ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True)
    worker_id = Column(Text, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    cancel_requested_at = Column(DateTime(timezone=True), nullable=True)
    result_json = Column(JSONB, nullable=True)
    error_code = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    debug_log_path = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    artifacts = relationship("SpeechArtifact", back_populates="job", cascade="all, delete-orphan")
    speaker_mappings = relationship("SpeechSpeakerMapping", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("operation IN ('stt','tts')", name="check_speech_jobs_operation"),
        CheckConstraint("status IN ('queued','running','completed','failed','cancelled')", name="check_speech_jobs_status"),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_speech_jobs_progress"),
        Index("idx_speech_jobs_status_created_at", status, created_at),
        Index("idx_speech_jobs_operation_status", operation, status),
        Index("idx_speech_jobs_worker_id", worker_id),
        Index("idx_speech_jobs_lease_expires_at", lease_expires_at),
        Index("idx_speech_jobs_reference_source_id", reference_source_id),
    )


class SpeechPreset(Base):
    __tablename__ = "speech_presets"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    operation = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    config_json = Column(JSONB, nullable=False, server_default="{}")
    is_builtin = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("operation IN ('stt','tts')", name="check_speech_presets_operation"),
        UniqueConstraint("operation", "name", name="uq_speech_presets_operation_name"),
    )


class SpeechArtifact(Base):
    __tablename__ = "speech_artifacts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    speech_job_id = Column(BigInteger, ForeignKey("speech_jobs.id", ondelete="CASCADE"), nullable=False)
    artifact_type = Column(Text, nullable=False)
    storage_key = Column(Text, nullable=False)
    filename = Column(Text, nullable=False)
    mime_type = Column(Text, nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("SpeechJob", back_populates="artifacts")

    __table_args__ = (Index("idx_speech_artifacts_job_id", speech_job_id),)


class SpeechSpeakerMapping(Base):
    __tablename__ = "speech_speaker_mappings"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transcript_id = Column(BigInteger, ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=True)
    speech_job_id = Column(BigInteger, ForeignKey("speech_jobs.id", ondelete="CASCADE"), nullable=True)
    raw_speaker = Column(Text, nullable=False)
    display_name = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    job = relationship("SpeechJob", back_populates="speaker_mappings")

    __table_args__ = (
        CheckConstraint("transcript_id IS NOT NULL OR speech_job_id IS NOT NULL", name="check_speech_speaker_mapping_owner"),
        UniqueConstraint("transcript_id", "raw_speaker", name="uq_speech_speaker_mapping_transcript_raw"),
        UniqueConstraint("speech_job_id", "raw_speaker", name="uq_speech_speaker_mapping_job_raw"),
        Index("idx_speech_speaker_mappings_transcript_id", transcript_id),
    )


class SpeechWorkerState(Base):
    __tablename__ = "speech_worker_state"

    worker_id = Column(Text, primary_key=True)
    capabilities_json = Column(JSONB, nullable=False, server_default="{}")
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
