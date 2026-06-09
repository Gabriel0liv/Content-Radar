"""add_transcript_versioning

Revision ID: 0005_add_transcript_versioning
Revises: 0004_add_references_transcripts
Create Date: 2026-06-09 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0005_add_transcript_versioning'
down_revision: Union[str, Sequence[str], None] = '0004_add_references_transcripts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Remove the unique constraint from transcripts
    op.drop_constraint("unique_transcripts_reference_source_id_full_text_hash", "transcripts", type_="unique")

    # 2. Add normal index on transcripts(reference_source_id, full_text_hash)
    op.create_index('idx_transcripts_ref_source_id_hash', 'transcripts', ['reference_source_id', 'full_text_hash'])

    # 3. Add new columns
    op.add_column('transcripts', sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('transcripts', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('transcripts', sa.Column('duplicate_of_transcript_id', sa.BigInteger(), sa.ForeignKey('transcripts.id', ondelete='SET NULL'), nullable=True))

    # 4. Create indexes
    op.create_index('idx_transcripts_ref_source_id_is_active', 'transcripts', ['reference_source_id', 'is_active'])
    op.create_index('idx_transcripts_ref_source_id_version_number', 'transcripts', ['reference_source_id', 'version_number'])

    # 5. Backfill existing transcripts
    # We use a standard SQL update query with CTE that works on Postgres
    op.execute("""
        WITH ranked_transcripts AS (
            SELECT 
                id,
                ROW_NUMBER() OVER (PARTITION BY reference_source_id ORDER BY created_at ASC, id ASC) as row_num,
                ROW_NUMBER() OVER (PARTITION BY reference_source_id ORDER BY created_at DESC, id DESC) as reverse_row_num
            FROM transcripts
        )
        UPDATE transcripts
        SET 
            version_number = rt.row_num,
            is_active = (rt.reverse_row_num = 1)
        FROM ranked_transcripts rt
        WHERE transcripts.id = rt.id
    """)


def downgrade() -> None:
    # 1. Drop indexes
    op.drop_index('idx_transcripts_ref_source_id_version_number', table_name='transcripts')
    op.drop_index('idx_transcripts_ref_source_id_is_active', table_name='transcripts')
    op.drop_index('idx_transcripts_ref_source_id_hash', table_name='transcripts')

    # 2. Drop columns
    op.drop_column('transcripts', 'duplicate_of_transcript_id')
    op.drop_column('transcripts', 'is_active')
    op.drop_column('transcripts', 'version_number')

    # 3. Re-add unique constraint
    op.create_unique_constraint(
        "unique_transcripts_reference_source_id_full_text_hash",
        "transcripts",
        ["reference_source_id", "full_text_hash"]
    )
