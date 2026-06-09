"""add_video_project_items

Revision ID: 0007_add_video_project_items
Revises: 0006_add_video_workshop
Create Date: 2026-06-09 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0007_add_video_project_items"
down_revision: Union[str, Sequence[str], None] = "0006_add_video_workshop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_project_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("video_project_id", sa.BigInteger(), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", sa.Text(), nullable=False, server_default="note"),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source_kind", sa.Text(), nullable=True, server_default="manual"),
        sa.Column("source_id", sa.BigInteger(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("idx_vpi_project_id", "video_project_items", ["video_project_id"])
    op.create_index("idx_vpi_item_type", "video_project_items", ["item_type"])
    op.create_index("idx_vpi_status", "video_project_items", ["status"])
    op.create_index("idx_vpi_pinned", "video_project_items", ["pinned"])
    op.create_index("idx_vpi_updated_at", "video_project_items", [sa.text("updated_at DESC")])

    op.add_column("video_project_board_nodes", sa.Column("item_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_video_project_board_nodes_item_id_video_project_items",
        "video_project_board_nodes",
        "video_project_items",
        ["item_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_video_project_board_nodes_item_id_video_project_items",
        "video_project_board_nodes",
        type_="foreignkey",
    )
    op.drop_column("video_project_board_nodes", "item_id")
    op.drop_index("idx_vpi_updated_at", table_name="video_project_items")
    op.drop_index("idx_vpi_pinned", table_name="video_project_items")
    op.drop_index("idx_vpi_status", table_name="video_project_items")
    op.drop_index("idx_vpi_item_type", table_name="video_project_items")
    op.drop_index("idx_vpi_project_id", table_name="video_project_items")
    op.drop_table("video_project_items")
