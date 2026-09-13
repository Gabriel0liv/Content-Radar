from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_case_radar_foundation"
down_revision = "0020_allow_whisperx_source"
branch_labels = None
depends_on = None


PLATFORMS = "'youtube','x','tiktok','instagram','reddit','web'"


def upgrade() -> None:
    op.create_table(
        "case_research_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("stage", sa.Text(), server_default="queued", nullable=False),
        sa.Column("progress_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider_coverage_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("discovered_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("clustered_cases", sa.Integer(), server_default="0", nullable=False),
        sa.Column("usable_cases", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rejected_cases", sa.Integer(), server_default="0", nullable=False),
        sa.Column("worker_id", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("errors_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("result_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','running','completed','partially_completed','failed','cancelled')",
            name="check_case_research_runs_status",
        ),
        sa.CheckConstraint(
            "stage IN ('queued','generating_queries','discovering','enriching_sources','collecting_social_context','clustering_cases','researching_cases','finalizing','completed','partially_completed','failed','cancelled')",
            name="check_case_research_runs_stage",
        ),
        sa.CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_case_research_runs_progress"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_case_research_runs_status_created_at", "case_research_runs", ["status", "created_at"])
    op.create_index("idx_case_research_runs_lease_expires_at", "case_research_runs", ["lease_expires_at"])
    op.create_index("idx_case_research_runs_worker_id", "case_research_runs", ["worker_id"])

    op.create_table(
        "case_research_queries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("target_platform", sa.Text(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="queued", nullable=False),
        sa.Column("result_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            f"target_platform IS NULL OR target_platform IN ({PLATFORMS})",
            name="check_case_research_queries_platform",
        ),
        sa.CheckConstraint("status IN ('queued','running','completed','failed','skipped')", name="check_case_research_queries_status"),
        sa.ForeignKeyConstraint(["run_id"], ["case_research_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "language", "target_platform", "intent", "query_text", name="uq_case_research_queries_run_query"),
    )
    op.create_index("idx_case_research_queries_run_id", "case_research_queries", ["run_id"])
    op.create_index("idx_case_research_queries_status", "case_research_queries", ["status"])

    op.create_table(
        "research_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("query_id", sa.BigInteger(), nullable=True),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("author_handle", sa.Text(), nullable=True),
        sa.Column("author_display_name", sa.Text(), nullable=True),
        sa.Column("title_or_caption", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=True),
        sa.Column("media_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("engagement_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("hashtags_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("relation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("discovery_method", sa.Text(), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("source_confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("content_item_id", sa.BigInteger(), nullable=True),
        sa.Column("reference_source_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(f"platform IN ({PLATFORMS})", name="check_research_sources_platform"),
        sa.CheckConstraint("source_confidence >= 0 AND source_confidence <= 1", name="check_research_sources_confidence"),
        sa.ForeignKeyConstraint(["run_id"], ["case_research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["query_id"], ["case_research_queries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["content_item_id"], ["content_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reference_source_id"], ["reference_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "platform", "external_id", name="uq_research_sources_run_platform_external_id"),
        sa.UniqueConstraint("run_id", "canonical_url", name="uq_research_sources_run_url"),
    )
    op.create_index("idx_research_sources_run_id", "research_sources", ["run_id"])
    op.create_index("idx_research_sources_query_id", "research_sources", ["query_id"])
    op.create_index("idx_research_sources_platform_external_id", "research_sources", ["platform", "external_id"])
    op.create_index("idx_research_sources_reference_source_id", "research_sources", ["reference_source_id"])
    op.create_index("idx_research_sources_content_item_id", "research_sources", ["content_item_id"])

    op.create_table(
        "research_cases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("provisional_title", sa.Text(), nullable=False),
        sa.Column("normalized_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="researching", nullable=False),
        sa.Column("alleged_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alleged_location", sa.Text(), nullable=True),
        sa.Column("earliest_known_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("origin_status", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("origin_confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("research_confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("likely_original_source_id", sa.BigInteger(), nullable=True),
        sa.Column("earliest_known_source_id", sa.BigInteger(), nullable=True),
        sa.Column("selected_primary_source_id", sa.BigInteger(), nullable=True),
        sa.Column("dossier_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("dossier_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("manual_notes", sa.Text(), nullable=True),
        sa.Column("already_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('researching','ready','approved','rejected','duplicate','already_used')", name="check_research_cases_status"),
        sa.CheckConstraint("origin_status IN ('unknown','likely','confirmed')", name="check_research_cases_origin_status"),
        sa.CheckConstraint("origin_confidence >= 0 AND origin_confidence <= 1", name="check_research_cases_origin_confidence"),
        sa.CheckConstraint("research_confidence >= 0 AND research_confidence <= 1", name="check_research_cases_research_confidence"),
        sa.ForeignKeyConstraint(["run_id"], ["case_research_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["likely_original_source_id"], ["research_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["earliest_known_source_id"], ["research_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["selected_primary_source_id"], ["research_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_research_cases_run_id", "research_cases", ["run_id"])
    op.create_index("idx_research_cases_status", "research_cases", ["status"])

    op.create_table(
        "case_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), server_default="unknown", nullable=False),
        sa.Column("provenance_confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('original_candidate','earliest_known','primary','mirror','repost','secondary_report','context','debunk','author_followup','unknown')", name="check_case_sources_role"),
        sa.CheckConstraint("provenance_confidence >= 0 AND provenance_confidence <= 1", name="check_case_sources_confidence"),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "source_id", name="uq_case_sources_case_source"),
    )
    op.create_index("idx_case_sources_case_id", "case_sources", ["case_id"])
    op.create_index("idx_case_sources_source_id", "case_sources", ["source_id"])

    op.create_table(
        "social_context_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("platform_item_id", sa.Text(), nullable=True),
        sa.Column("parent_social_context_id", sa.BigInteger(), nullable=True),
        sa.Column("author_handle", sa.Text(), nullable=True),
        sa.Column("author_display_name", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engagement_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("pinned", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("author_reply", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("urls_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("categories_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("usefulness_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_social_context_id"], ["social_context_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "platform_item_id", name="uq_social_context_source_platform_item"),
    )
    op.create_index("idx_social_context_items_source_id", "social_context_items", ["source_id"])
    op.create_index("idx_social_context_items_parent_id", "social_context_items", ["parent_social_context_id"])
    op.create_index("idx_social_context_items_usefulness", "social_context_items", [sa.text("usefulness_score DESC")])

    op.create_table(
        "case_claims",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("case_id", sa.BigInteger(), nullable=False),
        sa.Column("normalized_claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="unverified", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0", nullable=False),
        sa.Column("entities_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("extracted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_location", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('source_claimed','corroborated','contradicted','unverified')", name="check_case_claims_status"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_case_claims_confidence"),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_case_claims_case_id", "case_claims", ["case_id"])
    op.create_index("idx_case_claims_status", "case_claims", ["status"])

    op.create_table(
        "case_evidence",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("social_context_item_id", sa.BigInteger(), nullable=True),
        sa.Column("transcript_segment_id", sa.BigInteger(), nullable=True),
        sa.Column("stance", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("stance IN ('supports','contradicts','context_only')", name="check_case_evidence_stance"),
        sa.CheckConstraint("source_id IS NOT NULL OR social_context_item_id IS NOT NULL OR transcript_segment_id IS NOT NULL", name="check_case_evidence_has_target"),
        sa.ForeignKeyConstraint(["claim_id"], ["case_claims.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["social_context_item_id"], ["social_context_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transcript_segment_id"], ["transcript_segments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_case_evidence_claim_id", "case_evidence", ["claim_id"])
    op.create_index("idx_case_evidence_source_id", "case_evidence", ["source_id"])
    op.create_index("idx_case_evidence_social_item_id", "case_evidence", ["social_context_item_id"])
    op.create_index("idx_case_evidence_transcript_segment_id", "case_evidence", ["transcript_segment_id"])

    op.create_table(
        "media_fingerprints",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("fingerprint_type", sa.Text(), nullable=False),
        sa.Column("fingerprint_value", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["research_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "fingerprint_type", "fingerprint_value", name="uq_media_fingerprints_source_type_value"),
    )
    op.create_index("idx_media_fingerprints_source_id", "media_fingerprints", ["source_id"])
    op.create_index("idx_media_fingerprints_type_value", "media_fingerprints", ["fingerprint_type", "fingerprint_value"])


def downgrade() -> None:
    op.drop_index("idx_media_fingerprints_type_value", table_name="media_fingerprints")
    op.drop_index("idx_media_fingerprints_source_id", table_name="media_fingerprints")
    op.drop_table("media_fingerprints")

    op.drop_index("idx_case_evidence_transcript_segment_id", table_name="case_evidence")
    op.drop_index("idx_case_evidence_social_item_id", table_name="case_evidence")
    op.drop_index("idx_case_evidence_source_id", table_name="case_evidence")
    op.drop_index("idx_case_evidence_claim_id", table_name="case_evidence")
    op.drop_table("case_evidence")

    op.drop_index("idx_case_claims_status", table_name="case_claims")
    op.drop_index("idx_case_claims_case_id", table_name="case_claims")
    op.drop_table("case_claims")

    op.drop_index("idx_social_context_items_usefulness", table_name="social_context_items")
    op.drop_index("idx_social_context_items_parent_id", table_name="social_context_items")
    op.drop_index("idx_social_context_items_source_id", table_name="social_context_items")
    op.drop_table("social_context_items")

    op.drop_index("idx_case_sources_source_id", table_name="case_sources")
    op.drop_index("idx_case_sources_case_id", table_name="case_sources")
    op.drop_table("case_sources")

    op.drop_index("idx_research_cases_status", table_name="research_cases")
    op.drop_index("idx_research_cases_run_id", table_name="research_cases")
    op.drop_table("research_cases")

    op.drop_index("idx_research_sources_content_item_id", table_name="research_sources")
    op.drop_index("idx_research_sources_reference_source_id", table_name="research_sources")
    op.drop_index("idx_research_sources_platform_external_id", table_name="research_sources")
    op.drop_index("idx_research_sources_query_id", table_name="research_sources")
    op.drop_index("idx_research_sources_run_id", table_name="research_sources")
    op.drop_table("research_sources")

    op.drop_index("idx_case_research_queries_status", table_name="case_research_queries")
    op.drop_index("idx_case_research_queries_run_id", table_name="case_research_queries")
    op.drop_table("case_research_queries")

    op.drop_index("idx_case_research_runs_worker_id", table_name="case_research_runs")
    op.drop_index("idx_case_research_runs_lease_expires_at", table_name="case_research_runs")
    op.drop_index("idx_case_research_runs_status_created_at", table_name="case_research_runs")
    op.drop_table("case_research_runs")
