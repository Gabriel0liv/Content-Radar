"""add discovery terms

Revision ID: 0018_discovery_terms
Revises: 0017_structured_discovery
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0018_discovery_terms"
down_revision: Union[str, Sequence[str], None] = "0017_structured_discovery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discovery_terms",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("normalized_term", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("video_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("channel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("suppressed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("normalized_term", "type", "entity_id", name="uq_discovery_terms_identity"),
    )
    op.create_index("idx_discovery_terms_normalized_term", "discovery_terms", ["normalized_term"])
    op.create_index("idx_discovery_terms_type", "discovery_terms", ["type"])
    op.create_index("idx_discovery_terms_relevance_desc", "discovery_terms", [sa.text("relevance_score DESC")])


def downgrade() -> None:
    op.drop_index("idx_discovery_terms_relevance_desc", table_name="discovery_terms")
    op.drop_index("idx_discovery_terms_type", table_name="discovery_terms")
    op.drop_index("idx_discovery_terms_normalized_term", table_name="discovery_terms")
    op.drop_table("discovery_terms")
