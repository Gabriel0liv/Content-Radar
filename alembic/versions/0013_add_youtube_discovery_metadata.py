"""add youtube discovery metadata

Revision ID: 0013_youtube_discovery_metadata
Revises: 0012_reference_youtube_unique
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0013_youtube_discovery_metadata"
down_revision: Union[str, Sequence[str], None] = "0012_reference_youtube_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("channel_id", sa.Text(), nullable=True))
    op.add_column("content_items", sa.Column("youtube_video_id", sa.Text(), nullable=True))
    op.add_column("content_items", sa.Column("youtube_category_id", sa.Text(), nullable=True))
    op.add_column("content_items", sa.Column("youtube_category_name", sa.Text(), nullable=True))
    op.add_column("content_items", sa.Column("youtube_tags_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column("content_items", sa.Column("youtube_topics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column("content_items", sa.Column("topic_classification_version", sa.Text(), nullable=True))
    op.create_index("idx_content_items_channel_id", "content_items", ["channel_id"], unique=False)
    op.create_index("idx_content_items_youtube_video_id", "content_items", ["youtube_video_id"], unique=False)
    op.create_index("idx_content_items_youtube_category_id", "content_items", ["youtube_category_id"], unique=False)

    op.execute(
        """
        UPDATE content_items
        SET youtube_video_id = external_id
        WHERE lower(source) = 'youtube'
          AND external_id ~ '^[A-Za-z0-9_-]{11}$'
          AND youtube_video_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("idx_content_items_youtube_category_id", table_name="content_items")
    op.drop_index("idx_content_items_youtube_video_id", table_name="content_items")
    op.drop_index("idx_content_items_channel_id", table_name="content_items")
    op.drop_column("content_items", "topic_classification_version")
    op.drop_column("content_items", "youtube_topics_json")
    op.drop_column("content_items", "youtube_tags_json")
    op.drop_column("content_items", "youtube_category_name")
    op.drop_column("content_items", "youtube_category_id")
    op.drop_column("content_items", "youtube_video_id")
    op.drop_column("content_items", "channel_id")
