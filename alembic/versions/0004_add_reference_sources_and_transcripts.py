"""add_reference_sources_and_transcripts

Revision ID: 0004_add_references_transcripts
Revises: 0003_add_search_configs_and_runs
Create Date: 2026-06-08 10:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004_add_references_transcripts'
down_revision: Union[str, Sequence[str], None] = '0003_add_search_configs_and_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create reference_sources table
    op.create_table(
        'reference_sources',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('external_id', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('channel_title', sa.Text(), nullable=True),
        sa.Column('channel_id', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('view_count', sa.BigInteger(), nullable=True),
        sa.Column('like_count', sa.BigInteger(), nullable=True),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('language', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='new'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )

    # Check constraints for reference_sources
    op.create_check_constraint(
        constraint_name="check_reference_sources_source_type",
        table_name="reference_sources",
        condition="source_type IN ('youtube_video', 'manual')"
    )
    op.create_check_constraint(
        constraint_name="check_reference_sources_status",
        table_name="reference_sources",
        condition="status IN ('new', 'importing', 'transcribed', 'needs_audio_transcription', 'failed', 'archived')"
    )

    # Unique constraint for reference_sources
    op.create_unique_constraint(
        "unique_reference_sources_source_type_external_id",
        "reference_sources",
        ["source_type", "external_id"]
    )

    # Indexes for reference_sources
    op.create_index('idx_reference_sources_source_type', 'reference_sources', ['source_type'])
    op.create_index('idx_reference_sources_external_id', 'reference_sources', ['external_id'])
    op.create_index('idx_reference_sources_status', 'reference_sources', ['status'])
    op.create_index('idx_reference_sources_channel_title', 'reference_sources', ['channel_title'])
    op.create_index('idx_reference_sources_created_at_desc', 'reference_sources', [sa.text('created_at DESC')])

    # 2. Create reference_import_jobs table
    op.create_table(
        'reference_import_jobs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('reference_source_id', sa.BigInteger(), sa.ForeignKey('reference_sources.id', ondelete='CASCADE'), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='queued'),
        sa.Column('method', sa.Text(), nullable=False, server_default='yt_dlp_captions'),
        sa.Column('preferred_languages', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='["pt", "pt-BR", "en"]'),
        sa.Column('selected_language', sa.Text(), nullable=True),
        sa.Column('selected_caption_type', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Check constraints for reference_import_jobs
    op.create_check_constraint(
        constraint_name="check_reference_import_jobs_status",
        table_name="reference_import_jobs",
        condition="status IN ('queued', 'running', 'completed', 'failed', 'needs_audio_transcription')"
    )
    op.create_check_constraint(
        constraint_name="check_reference_import_jobs_method",
        table_name="reference_import_jobs",
        condition="method IN ('yt_dlp_metadata', 'yt_dlp_captions', 'manual', 'audio_to_text_future')"
    )

    # Indexes for reference_import_jobs
    op.create_index('idx_reference_import_jobs_reference_source_id', 'reference_import_jobs', ['reference_source_id'])
    op.create_index('idx_reference_import_jobs_status', 'reference_import_jobs', ['status'])
    op.create_index('idx_reference_import_jobs_created_at_desc', 'reference_import_jobs', [sa.text('created_at DESC')])

    # 3. Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('reference_source_id', sa.BigInteger(), sa.ForeignKey('reference_sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('import_job_id', sa.BigInteger(), sa.ForeignKey('reference_import_jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('language', sa.Text(), nullable=True),
        sa.Column('source_method', sa.Text(), nullable=False),
        sa.Column('full_text', sa.Text(), nullable=False),
        sa.Column('full_text_hash', sa.Text(), nullable=False),
        sa.Column('srt_text', sa.Text(), nullable=True),
        sa.Column('vtt_text', sa.Text(), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )

    # Check constraints for transcripts
    op.create_check_constraint(
        constraint_name="check_transcripts_source_method",
        table_name="transcripts",
        condition="source_method IN ('manual_caption', 'auto_caption', 'manual', 'audio_to_text_future')"
    )

    # Unique constraint for transcripts
    op.create_unique_constraint(
        "unique_transcripts_reference_source_id_full_text_hash",
        "transcripts",
        ["reference_source_id", "full_text_hash"]
    )

    # Indexes for transcripts
    op.create_index('idx_transcripts_reference_source_id', 'transcripts', ['reference_source_id'])

    # 4. Create transcript_segments table
    op.create_table(
        'transcript_segments',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('transcript_id', sa.BigInteger(), sa.ForeignKey('transcripts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('segment_index', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=True),
        sa.Column('end_time', sa.Float(), nullable=True),
        sa.Column('speaker', sa.Text(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('tokens_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )

    # Indexes for transcript_segments
    op.create_index('idx_transcript_segments_transcript_id', 'transcript_segments', ['transcript_id'])
    op.create_index('idx_transcript_segments_segment_index', 'transcript_segments', ['segment_index'])
    op.create_index('idx_transcript_segments_start_time', 'transcript_segments', ['start_time'])
    op.create_index('idx_transcript_segments_composite', 'transcript_segments', ['transcript_id', 'segment_index'])


def downgrade() -> None:
    # 4. Drop transcript_segments
    op.drop_index('idx_transcript_segments_composite', table_name='transcript_segments')
    op.drop_index('idx_transcript_segments_start_time', table_name='transcript_segments')
    op.drop_index('idx_transcript_segments_segment_index', table_name='transcript_segments')
    op.drop_index('idx_transcript_segments_transcript_id', table_name='transcript_segments')
    op.drop_table('transcript_segments')

    # 3. Drop transcripts
    op.drop_index('idx_transcripts_reference_source_id', table_name='transcripts')
    op.drop_constraint("unique_transcripts_reference_source_id_full_text_hash", "transcripts", type_="unique")
    op.drop_constraint("check_transcripts_source_method", "transcripts", type_="check")
    op.drop_table('transcripts')

    # 2. Drop reference_import_jobs
    op.drop_index('idx_reference_import_jobs_created_at_desc', table_name='reference_import_jobs')
    op.drop_index('idx_reference_import_jobs_status', table_name='reference_import_jobs')
    op.drop_index('idx_reference_import_jobs_reference_source_id', table_name='reference_import_jobs')
    op.drop_constraint("check_reference_import_jobs_method", "reference_import_jobs", type_="check")
    op.drop_constraint("check_reference_import_jobs_status", "reference_import_jobs", type_="check")
    op.drop_table('reference_import_jobs')

    # 1. Drop reference_sources
    op.drop_index('idx_reference_sources_created_at_desc', table_name='reference_sources')
    op.drop_index('idx_reference_sources_channel_title', table_name='reference_sources')
    op.drop_index('idx_reference_sources_status', table_name='reference_sources')
    op.drop_index('idx_reference_sources_external_id', table_name='reference_sources')
    op.drop_index('idx_reference_sources_source_type', table_name='reference_sources')
    op.drop_constraint("unique_reference_sources_source_type_external_id", "reference_sources", type_="unique")
    op.drop_constraint("check_reference_sources_status", "reference_sources", type_="check")
    op.drop_constraint("check_reference_sources_source_type", "reference_sources", type_="check")
    op.drop_table('reference_sources')
