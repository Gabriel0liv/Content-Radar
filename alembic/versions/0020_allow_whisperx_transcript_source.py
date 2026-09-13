from alembic import op
import sqlalchemy as sa


revision = "0020_allow_whisperx_source"
down_revision = "0019_speech_job_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("check_transcripts_source_method", "transcripts", type_="check")
    op.create_check_constraint(
        "check_transcripts_source_method",
        "transcripts",
        "source_method IN ('manual_caption', 'auto_caption', 'manual', 'audio_to_text_future', 'whisperx')",
    )


def downgrade() -> None:
    op.drop_constraint("check_transcripts_source_method", "transcripts", type_="check")
    op.create_check_constraint(
        "check_transcripts_source_method",
        "transcripts",
        "source_method IN ('manual_caption', 'auto_caption', 'manual', 'audio_to_text_future')",
    )
