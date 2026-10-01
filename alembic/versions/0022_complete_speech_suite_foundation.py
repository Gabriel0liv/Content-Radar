from alembic import op
import sqlalchemy as sa


revision = "0022_speech_suite_complete"
down_revision = "0021_case_radar_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("speech_jobs", sa.Column("retry_of_job_id", sa.BigInteger(), nullable=True))
    op.add_column("speech_jobs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_speech_jobs_retry_of_job_id",
        "speech_jobs",
        "speech_jobs",
        ["retry_of_job_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_speech_jobs_retry_of_job_id", "speech_jobs", ["retry_of_job_id"])
    op.create_index("idx_speech_jobs_archived_at", "speech_jobs", ["archived_at"])


def downgrade() -> None:
    op.drop_index("idx_speech_jobs_archived_at", table_name="speech_jobs")
    op.drop_index("idx_speech_jobs_retry_of_job_id", table_name="speech_jobs")
    op.drop_constraint("fk_speech_jobs_retry_of_job_id", "speech_jobs", type_="foreignkey")
    op.drop_column("speech_jobs", "archived_at")
    op.drop_column("speech_jobs", "retry_of_job_id")
