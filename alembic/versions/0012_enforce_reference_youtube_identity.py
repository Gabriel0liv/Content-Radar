"""enforce reference youtube identity

Revision ID: 0012_reference_youtube_unique
Revises: 0011_reference_youtube_identity
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_reference_youtube_unique"
down_revision: Union[str, Sequence[str], None] = "0011_reference_youtube_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    duplicates = connection.execute(
        sa.text(
            """
            SELECT youtube_video_id, array_agg(id ORDER BY id) AS source_ids
            FROM reference_sources
            WHERE source_type = 'youtube_video'
              AND youtube_video_id IS NOT NULL
            GROUP BY youtube_video_id
            HAVING count(*) > 1
            LIMIT 20
            """
        )
    ).fetchall()

    if duplicates:
        summary = "; ".join(
            f"{row.youtube_video_id}: {list(row.source_ids)}" for row in duplicates
        )
        raise RuntimeError(
            "Não é seguro aplicar a unicidade de youtube_video_id enquanto existirem "
            f"referências duplicadas. Execute a reconciliação primeiro. Duplicatas: {summary}"
        )

    op.create_index(
        "uq_reference_sources_youtube_video_id",
        "reference_sources",
        ["youtube_video_id"],
        unique=True,
        postgresql_where=sa.text("source_type = 'youtube_video' AND youtube_video_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_reference_sources_youtube_video_id", table_name="reference_sources")
