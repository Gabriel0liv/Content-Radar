"""add radar performance metrics

Revision ID: 0016_radar_performance
Revises: 0015_channel_profiles
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_radar_performance"
down_revision: Union[str, Sequence[str], None] = "0015_channel_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("performance_ratio", sa.Float(), nullable=True))
    op.add_column(
        "content_items",
        sa.Column("performance_baseline_samples", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_content_items_performance_ratio_desc",
        "content_items",
        [sa.text("performance_ratio DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_content_items_performance_ratio_desc", table_name="content_items")
    op.drop_column("content_items", "performance_baseline_samples")
    op.drop_column("content_items", "performance_ratio")
