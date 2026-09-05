from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_speech_job_foundation"
down_revision = "0018_discovery_terms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speech_jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("stage", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_message", sa.Text(), nullable=True),
        sa.Column("requested_config_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("resolved_config_json", postgresql.JSONB(), nullable=True),
        sa.Column("input_path", sa.Text(), nullable=True),
        sa.Column("reference_source_id", sa.BigInteger(), sa.ForeignKey("reference_sources.id", ondelete="SET NULL"), nullable=True),
        sa.Column("transcript_id", sa.BigInteger(), sa.ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("worker_id", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("debug_log_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("operation IN ('stt','tts')", name="check_speech_jobs_operation"),
        sa.CheckConstraint("status IN ('queued','running','completed','failed','cancelled')", name="check_speech_jobs_status"),
        sa.CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="check_speech_jobs_progress"),
    )
    op.create_index("idx_speech_jobs_status_created_at", "speech_jobs", ["status", "created_at"])
    op.create_index("idx_speech_jobs_operation_status", "speech_jobs", ["operation", "status"])
    op.create_index("idx_speech_jobs_worker_id", "speech_jobs", ["worker_id"])
    op.create_index("idx_speech_jobs_lease_expires_at", "speech_jobs", ["lease_expires_at"])
    op.create_index("idx_speech_jobs_reference_source_id", "speech_jobs", ["reference_source_id"])

    op.create_table(
        "speech_presets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("operation IN ('stt','tts')", name="check_speech_presets_operation"),
        sa.UniqueConstraint("operation", "name", name="uq_speech_presets_operation_name"),
    )

    op.create_table(
        "speech_artifacts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("speech_job_id", sa.BigInteger(), sa.ForeignKey("speech_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_speech_artifacts_job_id", "speech_artifacts", ["speech_job_id"])

    op.create_table(
        "speech_speaker_mappings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("transcript_id", sa.BigInteger(), sa.ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("speech_job_id", sa.BigInteger(), sa.ForeignKey("speech_jobs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("raw_speaker", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("transcript_id IS NOT NULL OR speech_job_id IS NOT NULL", name="check_speech_speaker_mapping_owner"),
        sa.UniqueConstraint("transcript_id", "raw_speaker", name="uq_speech_speaker_mapping_transcript_raw"),
        sa.UniqueConstraint("speech_job_id", "raw_speaker", name="uq_speech_speaker_mapping_job_raw"),
    )
    op.create_index("idx_speech_speaker_mappings_transcript_id", "speech_speaker_mappings", ["transcript_id"])

    op.create_table(
        "speech_worker_state",
        sa.Column("worker_id", sa.Text(), primary_key=True),
        sa.Column("capabilities_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("speech_worker_state")
    op.drop_index("idx_speech_speaker_mappings_transcript_id", table_name="speech_speaker_mappings")
    op.drop_table("speech_speaker_mappings")
    op.drop_index("idx_speech_artifacts_job_id", table_name="speech_artifacts")
    op.drop_table("speech_artifacts")
    op.drop_table("speech_presets")
    op.drop_index("idx_speech_jobs_reference_source_id", table_name="speech_jobs")
    op.drop_index("idx_speech_jobs_lease_expires_at", table_name="speech_jobs")
    op.drop_index("idx_speech_jobs_worker_id", table_name="speech_jobs")
    op.drop_index("idx_speech_jobs_operation_status", table_name="speech_jobs")
    op.drop_index("idx_speech_jobs_status_created_at", table_name="speech_jobs")
    op.drop_table("speech_jobs")
