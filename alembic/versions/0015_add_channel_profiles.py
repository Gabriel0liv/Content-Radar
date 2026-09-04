"""add channel profiles

Revision ID: 0015_channel_profiles
Revises: 0014_topic_taxonomy
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0015_channel_profiles"
down_revision: Union[str, Sequence[str], None] = "0014_topic_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channel_profiles",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("channel_title", sa.Text(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dominant_topics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column("recent_views_median", sa.Float(), nullable=True),
        sa.Column("recent_views_per_day_median", sa.Float(), nullable=True),
        sa.Column("recent_age_adjusted_samples", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_profiled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("channel_id", name="uq_channel_profiles_channel_id"),
    )
    op.create_index("idx_channel_profiles_channel_id", "channel_profiles", ["channel_id"])
    op.create_index("idx_channel_profiles_last_profiled_at", "channel_profiles", ["last_profiled_at"])


def downgrade() -> None:
    op.drop_index("idx_channel_profiles_last_profiled_at", table_name="channel_profiles")
    op.drop_index("idx_channel_profiles_channel_id", table_name="channel_profiles")
    op.drop_table("channel_profiles")
