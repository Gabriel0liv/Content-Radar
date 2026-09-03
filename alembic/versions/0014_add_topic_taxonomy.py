"""add topic taxonomy

Revision ID: 0014_topic_taxonomy
Revises: 0013_youtube_discovery_metadata
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0014_topic_taxonomy"
down_revision: Union[str, Sequence[str], None] = "0013_youtube_discovery_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.BigInteger(), sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint("type IN ('topic', 'subtopic', 'format', 'series')", name="check_topics_type"),
        sa.CheckConstraint("status IN ('active', 'hidden', 'archived')", name="check_topics_status"),
        sa.UniqueConstraint("normalized_name", "type", "parent_id", name="uq_topics_normalized_type_parent"),
    )
    op.create_index("idx_topics_normalized_name", "topics", ["normalized_name"])
    op.create_index("idx_topics_type", "topics", ["type"])

    op.create_table(
        "content_item_topics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("content_item_id", sa.BigInteger(), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.BigInteger(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("signals_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column("classifier_version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("content_item_id", "topic_id", name="uq_content_item_topics_item_topic"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="check_content_item_topics_confidence"),
    )
    op.create_index("idx_content_item_topics_content_item_id", "content_item_topics", ["content_item_id"])
    op.create_index("idx_content_item_topics_topic_id", "content_item_topics", ["topic_id"])
    op.create_index("idx_content_item_topics_confidence", "content_item_topics", ["confidence"])

    topics = sa.table(
        "topics",
        sa.column("name", sa.Text()),
        sa.column("normalized_name", sa.Text()),
        sa.column("type", sa.Text()),
        sa.column("parent_id", sa.BigInteger()),
        sa.column("status", sa.Text()),
    )
    op.bulk_insert(topics, [
        {"name": "Minecraft", "normalized_name": "minecraft", "type": "topic", "parent_id": None, "status": "active"},
        {"name": "Horror", "normalized_name": "horror", "type": "topic", "parent_id": None, "status": "active"},
        {"name": "Analog Horror", "normalized_name": "analog horror", "type": "subtopic", "parent_id": None, "status": "active"},
        {"name": "ARG", "normalized_name": "arg", "type": "subtopic", "parent_id": None, "status": "active"},
        {"name": "Hardcore", "normalized_name": "hardcore", "type": "subtopic", "parent_id": None, "status": "active"},
        {"name": "Modded Minecraft", "normalized_name": "modded minecraft", "type": "subtopic", "parent_id": None, "status": "active"},
        {"name": "SMP", "normalized_name": "smp", "type": "format", "parent_id": None, "status": "active"},
        {"name": "Roleplay", "normalized_name": "roleplay", "type": "format", "parent_id": None, "status": "active"},
        {"name": "Lore", "normalized_name": "lore", "type": "format", "parent_id": None, "status": "active"},
        {"name": "Series", "normalized_name": "series", "type": "format", "parent_id": None, "status": "active"},
        {"name": "Challenge", "normalized_name": "challenge", "type": "format", "parent_id": None, "status": "active"},
    ])


def downgrade() -> None:
    op.drop_index("idx_content_item_topics_confidence", table_name="content_item_topics")
    op.drop_index("idx_content_item_topics_topic_id", table_name="content_item_topics")
    op.drop_index("idx_content_item_topics_content_item_id", table_name="content_item_topics")
    op.drop_table("content_item_topics")
    op.drop_index("idx_topics_type", table_name="topics")
    op.drop_index("idx_topics_normalized_name", table_name="topics")
    op.drop_table("topics")
