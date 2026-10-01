from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0023_speech_speaker_profiles"
down_revision = "0022_speech_suite_complete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "speech_speaker_profiles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("mapping_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_speech_speaker_profiles_name"),
    )
    op.create_index("idx_speech_speaker_profiles_name", "speech_speaker_profiles", ["name"])


def downgrade() -> None:
    op.drop_index("idx_speech_speaker_profiles_name", table_name="speech_speaker_profiles")
    op.drop_table("speech_speaker_profiles")
