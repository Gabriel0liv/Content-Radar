from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.session import Base


PLATFORM_CHECK = "platform IN ('youtube','x','tiktok','instagram','reddit','web')"


class CaseResearchRun(Base):
    __tablename__ = "case_research_runs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    status = Column(Text, nullable=False, server_default="queued")
    stage = Column(Text, nullable=False, server_default="queued")
    progress_percent = Column(Integer, nullable=False, server_default="0")
    progress_message = Column(Text, nullable=True)
    request_json = Column(JSONB, nullable=False)
    provider_coverage_json = Column(JSONB, nullable=False, server_default="{}")
    discovered_candidates = Column(Integer, nullable=False, server_default="0")
    clustered_cases = Column(Integer, nullable=False, server_default="0")
    usable_cases = Column(Integer, nullable=False, server_default="0")
    rejected_cases = Column(Integer, nullable=False, server_default="0")
    worker_id = Column(Text, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    cancel_requested_at = Column(DateTime(timezone=True), nullable=True)
    errors_json = Column(JSONB, nullable=False, server_default="[]")
    result_summary_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    queries = relationship("CaseResearchQuery", back_populates="run", cascade="all, delete-orphan")
    sources = relationship("ResearchSource", back_populates="run", cascade="all, delete-orphan")
    cases = relationship("ResearchCase", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','completed','partially_completed','failed','cancelled')",
            name="check_case_research_runs_status",
        ),
        CheckConstraint(
            "stage IN ('queued','generating_queries','discovering','enriching_sources','collecting_social_context','clustering_cases','researching_cases','finalizing','completed','partially_completed','failed','cancelled')",
            name="check_case_research_runs_stage",
        ),
        CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_case_research_runs_progress"),
        Index("idx_case_research_runs_status_created_at", status, created_at),
        Index("idx_case_research_runs_lease_expires_at", lease_expires_at),
        Index("idx_case_research_runs_worker_id", worker_id),
    )


class CaseResearchQuery(Base):
    __tablename__ = "case_research_queries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey("case_research_runs.id", ondelete="CASCADE"), nullable=False)
    language = Column(Text, nullable=False)
    target_platform = Column(Text, nullable=True)
    query_text = Column(Text, nullable=False)
    intent = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="queued")
    result_count = Column(Integer, nullable=False, server_default="0")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    run = relationship("CaseResearchRun", back_populates="queries")
    sources = relationship("ResearchSource", back_populates="query")

    __table_args__ = (
        CheckConstraint(
            "target_platform IS NULL OR target_platform IN ('youtube','x','tiktok','instagram','reddit','web')",
            name="check_case_research_queries_platform",
        ),
        CheckConstraint(
            "status IN ('queued','running','completed','failed','skipped')",
            name="check_case_research_queries_status",
        ),
        UniqueConstraint(
            "run_id", "language", "target_platform", "intent", "query_text",
            name="uq_case_research_queries_run_query",
        ),
        Index("idx_case_research_queries_run_id", run_id),
        Index("idx_case_research_queries_status", status),
    )


class ResearchSource(Base):
    __tablename__ = "research_sources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey("case_research_runs.id", ondelete="CASCADE"), nullable=False)
    query_id = Column(BigInteger, ForeignKey("case_research_queries.id", ondelete="SET NULL"), nullable=True)
    platform = Column(Text, nullable=False)
    external_id = Column(Text, nullable=True)
    canonical_url = Column(Text, nullable=False)
    author_handle = Column(Text, nullable=True)
    author_display_name = Column(Text, nullable=True)
    title_or_caption = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    discovered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    media_type = Column(Text, nullable=True)
    media_json = Column(JSONB, nullable=False, server_default="{}")
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    language = Column(Text, nullable=True)
    engagement_json = Column(JSONB, nullable=False, server_default="{}")
    hashtags_json = Column(JSONB, nullable=False, server_default="[]")
    relation_json = Column(JSONB, nullable=True)
    discovery_method = Column(Text, nullable=False)
    raw_json = Column(JSONB, nullable=False, server_default="{}")
    source_confidence = Column(Float, nullable=False, server_default="0")
    content_item_id = Column(BigInteger, ForeignKey("content_items.id", ondelete="SET NULL"), nullable=True)
    reference_source_id = Column(BigInteger, ForeignKey("reference_sources.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    run = relationship("CaseResearchRun", back_populates="sources")
    query = relationship("CaseResearchQuery", back_populates="sources")
    case_links = relationship("CaseSource", back_populates="source", cascade="all, delete-orphan")
    social_items = relationship("SocialContextItem", back_populates="source", cascade="all, delete-orphan")
    fingerprints = relationship("MediaFingerprint", back_populates="source", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(PLATFORM_CHECK, name="check_research_sources_platform"),
        CheckConstraint("source_confidence >= 0 AND source_confidence <= 1", name="check_research_sources_confidence"),
        UniqueConstraint("run_id", "platform", "external_id", name="uq_research_sources_run_platform_external_id"),
        UniqueConstraint("run_id", "canonical_url", name="uq_research_sources_run_url"),
        Index("idx_research_sources_run_id", run_id),
        Index("idx_research_sources_query_id", query_id),
        Index("idx_research_sources_platform_external_id", platform, external_id),
        Index("idx_research_sources_reference_source_id", reference_source_id),
        Index("idx_research_sources_content_item_id", content_item_id),
    )


class ResearchCase(Base):
    __tablename__ = "research_cases"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(BigInteger, ForeignKey("case_research_runs.id", ondelete="CASCADE"), nullable=False)
    provisional_title = Column(Text, nullable=False)
    normalized_summary = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default="researching")
    alleged_date = Column(DateTime(timezone=True), nullable=True)
    alleged_location = Column(Text, nullable=True)
    earliest_known_date = Column(DateTime(timezone=True), nullable=True)
    origin_status = Column(Text, nullable=False, server_default="unknown")
    origin_confidence = Column(Float, nullable=False, server_default="0")
    research_confidence = Column(Float, nullable=False, server_default="0")
    likely_original_source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="SET NULL"), nullable=True)
    earliest_known_source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="SET NULL"), nullable=True)
    selected_primary_source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="SET NULL"), nullable=True)
    dossier_version = Column(Integer, nullable=False, server_default="1")
    dossier_json = Column(JSONB, nullable=True)
    manual_notes = Column(Text, nullable=True)
    already_used = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    run = relationship("CaseResearchRun", back_populates="cases")
    source_links = relationship("CaseSource", back_populates="case", cascade="all, delete-orphan")
    claims = relationship("CaseClaim", back_populates="case", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('researching','ready','approved','rejected','duplicate','already_used')",
            name="check_research_cases_status",
        ),
        CheckConstraint("origin_status IN ('unknown','likely','confirmed')", name="check_research_cases_origin_status"),
        CheckConstraint("origin_confidence >= 0 AND origin_confidence <= 1", name="check_research_cases_origin_confidence"),
        CheckConstraint("research_confidence >= 0 AND research_confidence <= 1", name="check_research_cases_research_confidence"),
        Index("idx_research_cases_run_id", run_id),
        Index("idx_research_cases_status", status),
    )


class CaseSource(Base):
    __tablename__ = "case_sources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("research_cases.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False, server_default="unknown")
    provenance_confidence = Column(Float, nullable=False, server_default="0")
    reason = Column(Text, nullable=True)
    evidence_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    case = relationship("ResearchCase", back_populates="source_links")
    source = relationship("ResearchSource", back_populates="case_links")

    __table_args__ = (
        CheckConstraint(
            "role IN ('original_candidate','earliest_known','primary','mirror','repost','secondary_report','context','debunk','author_followup','unknown')",
            name="check_case_sources_role",
        ),
        CheckConstraint(
            "provenance_confidence >= 0 AND provenance_confidence <= 1",
            name="check_case_sources_confidence",
        ),
        UniqueConstraint("case_id", "source_id", name="uq_case_sources_case_source"),
        Index("idx_case_sources_case_id", case_id),
        Index("idx_case_sources_source_id", source_id),
    )


class SocialContextItem(Base):
    __tablename__ = "social_context_items"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=False)
    platform_item_id = Column(Text, nullable=True)
    parent_social_context_id = Column(BigInteger, ForeignKey("social_context_items.id", ondelete="CASCADE"), nullable=True)
    author_handle = Column(Text, nullable=True)
    author_display_name = Column(Text, nullable=True)
    body = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    engagement_json = Column(JSONB, nullable=False, server_default="{}")
    pinned = Column(Boolean, nullable=False, server_default="false")
    author_reply = Column(Boolean, nullable=False, server_default="false")
    urls_json = Column(JSONB, nullable=False, server_default="[]")
    categories_json = Column(JSONB, nullable=False, server_default="[]")
    usefulness_score = Column(Float, nullable=False, server_default="0")
    raw_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source = relationship("ResearchSource", back_populates="social_items")
    parent = relationship("SocialContextItem", remote_side=[id], back_populates="children")
    children = relationship("SocialContextItem", back_populates="parent", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_id", "platform_item_id", name="uq_social_context_source_platform_item"),
        Index("idx_social_context_items_source_id", source_id),
        Index("idx_social_context_items_parent_id", parent_social_context_id),
        Index("idx_social_context_items_usefulness", usefulness_score.desc()),
    )


class CaseClaim(Base):
    __tablename__ = "case_claims"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    case_id = Column(BigInteger, ForeignKey("research_cases.id", ondelete="CASCADE"), nullable=False)
    normalized_claim_text = Column(Text, nullable=False)
    claim_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="unverified")
    confidence = Column(Float, nullable=False, server_default="0")
    entities_json = Column(JSONB, nullable=False, server_default="{}")
    extracted_date = Column(DateTime(timezone=True), nullable=True)
    extracted_location = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    case = relationship("ResearchCase", back_populates="claims")
    evidence = relationship("CaseEvidence", back_populates="claim", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "status IN ('source_claimed','corroborated','contradicted','unverified')",
            name="check_case_claims_status",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_case_claims_confidence"),
        Index("idx_case_claims_case_id", case_id),
        Index("idx_case_claims_status", status),
    )


class CaseEvidence(Base):
    __tablename__ = "case_evidence"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    claim_id = Column(BigInteger, ForeignKey("case_claims.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=True)
    social_context_item_id = Column(BigInteger, ForeignKey("social_context_items.id", ondelete="CASCADE"), nullable=True)
    transcript_segment_id = Column(BigInteger, ForeignKey("transcript_segments.id", ondelete="SET NULL"), nullable=True)
    stance = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    claim = relationship("CaseClaim", back_populates="evidence")

    __table_args__ = (
        CheckConstraint("stance IN ('supports','contradicts','context_only')", name="check_case_evidence_stance"),
        CheckConstraint(
            "source_id IS NOT NULL OR social_context_item_id IS NOT NULL OR transcript_segment_id IS NOT NULL",
            name="check_case_evidence_has_target",
        ),
        Index("idx_case_evidence_claim_id", claim_id),
        Index("idx_case_evidence_source_id", source_id),
        Index("idx_case_evidence_social_item_id", social_context_item_id),
        Index("idx_case_evidence_transcript_segment_id", transcript_segment_id),
    )


class MediaFingerprint(Base):
    __tablename__ = "media_fingerprints"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_id = Column(BigInteger, ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=False)
    fingerprint_type = Column(Text, nullable=False)
    fingerprint_value = Column(Text, nullable=False)
    algorithm = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=False, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source = relationship("ResearchSource", back_populates="fingerprints")

    __table_args__ = (
        UniqueConstraint(
            "source_id", "fingerprint_type", "fingerprint_value",
            name="uq_media_fingerprints_source_type_value",
        ),
        Index("idx_media_fingerprints_source_id", source_id),
        Index("idx_media_fingerprints_type_value", fingerprint_type, fingerprint_value),
    )
