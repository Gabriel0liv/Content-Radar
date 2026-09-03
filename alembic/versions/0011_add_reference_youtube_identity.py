"""add reference youtube identity

Revision ID: 0011_reference_youtube_identity
Revises: 0010_canva_oauth
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_reference_youtube_identity"
down_revision: Union[str, Sequence[str], None] = "0010_canva_oauth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reference_sources", sa.Column("youtube_video_id", sa.Text(), nullable=True))
    op.create_index(
        "idx_reference_sources_youtube_video_id",
        "reference_sources",
        ["youtube_video_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE reference_sources
        SET youtube_video_id = external_id
        WHERE source_type = 'youtube_video'
          AND external_id IS NOT NULL
          AND external_id ~ '^[A-Za-z0-9_-]{11}$'
          AND youtube_video_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("idx_reference_sources_youtube_video_id", table_name="reference_sources")
    op.drop_column("reference_sources", "youtube_video_id")
