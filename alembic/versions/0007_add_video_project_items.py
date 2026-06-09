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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "video_project_items" not in inspector.get_table_names():
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

    op.execute("CREATE INDEX IF NOT EXISTS idx_vpi_project_id ON video_project_items(video_project_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vpi_item_type ON video_project_items(item_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vpi_status ON video_project_items(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vpi_pinned ON video_project_items(pinned)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vpi_updated_at ON video_project_items(updated_at DESC)")

    board_node_columns = {column["name"] for column in inspector.get_columns("video_project_board_nodes")}
    if "item_id" not in board_node_columns:
        op.add_column("video_project_board_nodes", sa.Column("item_id", sa.BigInteger(), nullable=True))

    board_node_fks = {fk["name"] for fk in inspector.get_foreign_keys("video_project_board_nodes")}
    if "fk_video_project_board_nodes_item_id_video_project_items" not in board_node_fks:
        op.create_foreign_key(
            "fk_video_project_board_nodes_item_id_video_project_items",
            "video_project_board_nodes",
            "video_project_items",
            ["item_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "video_project_board_nodes" in inspector.get_table_names():
        board_node_fks = {fk["name"] for fk in inspector.get_foreign_keys("video_project_board_nodes")}
        if "fk_video_project_board_nodes_item_id_video_project_items" in board_node_fks:
            op.drop_constraint(
                "fk_video_project_board_nodes_item_id_video_project_items",
                "video_project_board_nodes",
                type_="foreignkey",
            )

        board_node_columns = {column["name"] for column in inspector.get_columns("video_project_board_nodes")}
        if "item_id" in board_node_columns:
            op.drop_column("video_project_board_nodes", "item_id")

    if "video_project_items" in inspector.get_table_names():
        op.execute("DROP INDEX IF EXISTS idx_vpi_updated_at")
        op.execute("DROP INDEX IF EXISTS idx_vpi_pinned")
        op.execute("DROP INDEX IF EXISTS idx_vpi_status")
        op.execute("DROP INDEX IF EXISTS idx_vpi_item_type")
        op.execute("DROP INDEX IF EXISTS idx_vpi_project_id")
        op.drop_table("video_project_items")
