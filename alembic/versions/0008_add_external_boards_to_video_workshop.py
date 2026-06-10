"""add_external_boards_to_video_workshop

Revision ID: 0008_external_boards
Revises: 0007_add_video_project_items
Create Date: 2026-06-10 00:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0008_external_boards"
down_revision: Union[str, Sequence[str], None] = "0007_add_video_project_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "video_project_external_boards" not in inspector.get_table_names():
        op.create_table(
            "video_project_external_boards",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("video_project_id", sa.BigInteger(), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.Text(), nullable=False),
            sa.Column("external_id", sa.Text(), nullable=False),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("view_url", sa.Text(), nullable=True),
            sa.Column("edit_url", sa.Text(), nullable=True),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.CheckConstraint("provider IN ('miro', 'canva')", name="check_video_project_external_boards_provider"),
            sa.UniqueConstraint("provider", "external_id", name="uq_video_project_external_boards_provider_external_id"),
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_project_external_boards_project_id "
        "ON video_project_external_boards(video_project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_video_project_external_boards_provider "
        "ON video_project_external_boards(provider)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "video_project_external_boards" in inspector.get_table_names():
        op.execute("DROP INDEX IF EXISTS idx_video_project_external_boards_provider")
        op.execute("DROP INDEX IF EXISTS idx_video_project_external_boards_project_id")
        op.drop_table("video_project_external_boards")
