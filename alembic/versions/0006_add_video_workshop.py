"""add_video_workshop

Revision ID: 0006_add_video_workshop
Revises: 0005_add_transcript_versioning
Create Date: 2026-06-09 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0006_add_video_workshop'
down_revision: Union[str, Sequence[str], None] = '0005_add_transcript_versioning'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create table video_projects
    op.create_table(
        'video_projects',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('working_title', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('niche', sa.Text(), nullable=True),
        sa.Column('target_platform', sa.Text(), nullable=True),
        sa.Column('video_format', sa.Text(), nullable=True),
        sa.Column('target_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='idea'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('script_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('script_content_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint(
            "status IN ('idea', 'researching', 'scripting', 'reviewing', 'ready', 'produced', 'archived')",
            name='check_video_projects_status'
        )
    )
    # Indexes on video_projects
    op.create_index('idx_video_projects_status', 'video_projects', ['status'])
    op.create_index('idx_video_projects_niche', 'video_projects', ['niche'])
    op.create_index('idx_video_projects_created_at_desc', 'video_projects', [sa.text('created_at DESC')])
    op.create_index('idx_video_projects_updated_at_desc', 'video_projects', [sa.text('updated_at DESC')])

    # 2. Create table video_project_notes
    op.create_table(
        'video_project_notes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('video_project_id', sa.BigInteger(), sa.ForeignKey('video_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_type', sa.Text(), nullable=False, server_default='idea'),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='open'),
        sa.Column('pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint(
            "note_type IN ('idea', 'research', 'script_note', 'production_note', 'music_idea', 'thumbnail_idea', 'editing_note', 'todo', 'other')",
            name='check_video_project_notes_note_type'
        ),
        sa.CheckConstraint(
            "status IN ('open', 'done', 'archived')",
            name='check_video_project_notes_status'
        )
    )
    # Indexes on video_project_notes
    op.create_index('idx_video_project_notes_project_id', 'video_project_notes', ['video_project_id'])
    op.create_index('idx_video_project_notes_note_type', 'video_project_notes', ['note_type'])
    op.create_index('idx_video_project_notes_status', 'video_project_notes', ['status'])
    op.create_index('idx_video_project_notes_pinned', 'video_project_notes', ['pinned'])
    op.create_index('idx_video_project_notes_created_at_desc', 'video_project_notes', [sa.text('created_at DESC')])

    # 3. Create table video_project_references
    op.create_table(
        'video_project_references',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('video_project_id', sa.BigInteger(), sa.ForeignKey('video_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content_item_id', sa.BigInteger(), sa.ForeignKey('content_items.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reference_source_id', sa.BigInteger(), sa.ForeignKey('reference_sources.id', ondelete='SET NULL'), nullable=True),
        sa.Column('transcript_id', sa.BigInteger(), sa.ForeignKey('transcripts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('external_url', sa.Text(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    # Indexes on video_project_references
    op.create_index('idx_video_project_references_project_id', 'video_project_references', ['video_project_id'])
    op.create_index('idx_video_project_references_content_item_id', 'video_project_references', ['content_item_id'])
    op.create_index('idx_video_project_references_reference_source_id', 'video_project_references', ['reference_source_id'])
    op.create_index('idx_video_project_references_transcript_id', 'video_project_references', ['transcript_id'])

    # 4. Create table video_project_audio_ideas
    op.create_table(
        'video_project_audio_ideas',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('video_project_id', sa.BigInteger(), sa.ForeignKey('video_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('audio_title', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.Text(), nullable=True),
        sa.Column('audio_type', sa.Text(), nullable=True),
        sa.Column('mood', sa.Text(), nullable=True),
        sa.Column('source_platform', sa.Text(), nullable=True),
        sa.Column('license_notes', sa.Text(), nullable=True),
        sa.Column('usage_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    # Indexes on video_project_audio_ideas
    op.create_index('idx_video_project_audio_ideas_project_id', 'video_project_audio_ideas', ['video_project_id'])
    op.create_index('idx_video_project_audio_ideas_audio_type', 'video_project_audio_ideas', ['audio_type'])
    op.create_index('idx_video_project_audio_ideas_mood', 'video_project_audio_ideas', ['mood'])

    # 5. Create table video_project_board_nodes
    op.create_table(
        'video_project_board_nodes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('video_project_id', sa.BigInteger(), sa.ForeignKey('video_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('node_key', sa.Text(), nullable=False),
        sa.Column('node_type', sa.Text(), nullable=False, server_default='note'),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('x', sa.Float(), nullable=False, server_default='0'),
        sa.Column('y', sa.Float(), nullable=False, server_default='0'),
        sa.Column('width', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('color', sa.Text(), nullable=True),
        sa.Column('data_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.UniqueConstraint('video_project_id', 'node_key', name='unique_video_project_board_nodes_project_id_node_key')
    )
    # Indexes on video_project_board_nodes
    op.create_index('idx_video_project_board_nodes_project_id', 'video_project_board_nodes', ['video_project_id'])
    op.create_index('idx_video_project_board_nodes_node_type', 'video_project_board_nodes', ['node_type'])

    # 6. Create table video_project_board_edges
    op.create_table(
        'video_project_board_edges',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('video_project_id', sa.BigInteger(), sa.ForeignKey('video_projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('edge_key', sa.Text(), nullable=False),
        sa.Column('source_node_key', sa.Text(), nullable=False),
        sa.Column('target_node_key', sa.Text(), nullable=False),
        sa.Column('label', sa.Text(), nullable=True),
        sa.Column('data_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.UniqueConstraint('video_project_id', 'edge_key', name='unique_video_project_board_edges_project_id_edge_key')
    )
    # Indexes on video_project_board_edges
    op.create_index('idx_video_project_board_edges_project_id', 'video_project_board_edges', ['video_project_id'])
    op.create_index('idx_video_project_board_edges_source', 'video_project_board_edges', ['source_node_key'])
    op.create_index('idx_video_project_board_edges_target', 'video_project_board_edges', ['target_node_key'])


def downgrade() -> None:
    op.drop_table('video_project_board_edges')
    op.drop_table('video_project_board_nodes')
    op.drop_table('video_project_audio_ideas')
    op.drop_table('video_project_references')
    op.drop_table('video_project_notes')
    op.drop_table('video_projects')
