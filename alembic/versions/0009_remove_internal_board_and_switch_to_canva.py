"""remove_internal_board_and_switch_to_canva

Revision ID: 0009_canva_only
Revises: 0008_external_boards
Create Date: 2026-06-10 11:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_canva_only"
down_revision: Union[str, Sequence[str], None] = "0008_external_boards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "video_project_board_edges"):
        op.execute("DROP INDEX IF EXISTS idx_video_project_board_edges_target")
        op.execute("DROP INDEX IF EXISTS idx_video_project_board_edges_source")
        op.execute("DROP INDEX IF EXISTS idx_video_project_board_edges_project_id")
        op.drop_table("video_project_board_edges")

    if _has_table(inspector, "video_project_board_nodes"):
        for fk in inspector.get_foreign_keys("video_project_board_nodes"):
            if (
                fk.get("referred_table") == "video_project_items"
                and "item_id" in (fk.get("constrained_columns") or [])
                and fk.get("name")
            ):
                op.drop_constraint(
                    fk["name"],
                    "video_project_board_nodes",
                    type_="foreignkey",
                )
        op.execute("DROP INDEX IF EXISTS idx_video_project_board_nodes_node_type")
        op.execute("DROP INDEX IF EXISTS idx_video_project_board_nodes_project_id")
        op.drop_table("video_project_board_nodes")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "video_project_board_nodes"):
        op.create_table(
            "video_project_board_nodes",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("video_project_id", sa.BigInteger(), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", sa.BigInteger(), nullable=True),
            sa.Column("node_key", sa.Text(), nullable=False),
            sa.Column("node_type", sa.Text(), nullable=False, server_default="note"),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("x", sa.Float(), nullable=False, server_default="0"),
            sa.Column("y", sa.Float(), nullable=False, server_default="0"),
            sa.Column("width", sa.Float(), nullable=True),
            sa.Column("height", sa.Float(), nullable=True),
            sa.Column("color", sa.Text(), nullable=True),
            sa.Column("data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.UniqueConstraint("video_project_id", "node_key", name="unique_video_project_board_nodes_project_id_node_key"),
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_project_board_nodes_project_id "
            "ON video_project_board_nodes(video_project_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_project_board_nodes_node_type "
            "ON video_project_board_nodes(node_type)"
        )
        if _has_table(inspector, "video_project_items"):
            op.create_foreign_key(
                "fk_video_project_board_nodes_item_id_video_project_items",
                "video_project_board_nodes",
                "video_project_items",
                ["item_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if not _has_table(inspector, "video_project_board_edges"):
        op.create_table(
            "video_project_board_edges",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("video_project_id", sa.BigInteger(), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("edge_key", sa.Text(), nullable=False),
            sa.Column("source_node_key", sa.Text(), nullable=False),
            sa.Column("target_node_key", sa.Text(), nullable=False),
            sa.Column("label", sa.Text(), nullable=True),
            sa.Column("data_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.UniqueConstraint("video_project_id", "edge_key", name="unique_video_project_board_edges_project_id_edge_key"),
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_project_board_edges_project_id "
            "ON video_project_board_edges(video_project_id)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_project_board_edges_source "
            "ON video_project_board_edges(source_node_key)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_video_project_board_edges_target "
            "ON video_project_board_edges(target_node_key)"
        )
