"""add structured discovery filters

Revision ID: 0017_structured_discovery
Revises: 0016_radar_performance
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0017_structured_discovery"
down_revision: Union[str, Sequence[str], None] = "0016_radar_performance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("search_configs", sa.Column("included_topic_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column("search_configs", sa.Column("excluded_topic_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column("search_configs", sa.Column("minimum_topic_confidence", sa.Float(), nullable=True, server_default="0.7"))
    op.add_column("search_configs", sa.Column("minimum_performance_ratio", sa.Float(), nullable=True))
    op.create_check_constraint(
        "check_search_configs_topic_confidence",
        "search_configs",
        "minimum_topic_confidence IS NULL OR (minimum_topic_confidence >= 0 AND minimum_topic_confidence <= 1)",
    )
    op.create_check_constraint(
        "check_search_configs_performance_ratio",
        "search_configs",
        "minimum_performance_ratio IS NULL OR minimum_performance_ratio >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("check_search_configs_performance_ratio", "search_configs", type_="check")
    op.drop_constraint("check_search_configs_topic_confidence", "search_configs", type_="check")
    op.drop_column("search_configs", "minimum_performance_ratio")
    op.drop_column("search_configs", "minimum_topic_confidence")
    op.drop_column("search_configs", "excluded_topic_ids")
    op.drop_column("search_configs", "included_topic_ids")
