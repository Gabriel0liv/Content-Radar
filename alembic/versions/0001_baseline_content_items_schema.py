"""baseline_content_items_schema

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-06-04 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_baseline'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create content_items table
    op.create_table(
        'content_items',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('external_id', sa.Text(), nullable=False),
        sa.Column('content_type', sa.Text(), nullable=False, server_default='video'),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('channel_title', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('views', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('likes', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('comments', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('views_per_day', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('score', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('topic_seed', sa.Text(), nullable=True),
        sa.Column('discovery_query', sa.Text(), nullable=True),
        sa.Column('language', sa.Text(), nullable=True),
        sa.Column('country_code', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=True, server_default='new'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('raw_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('selected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_reason', sa.Text(), nullable=True),
        sa.Column('production_notes', sa.Text(), nullable=True),
        sa.UniqueConstraint('source', 'external_id', name='unique_source_external_id')
    )
    
    # Create indexes for content_items
    op.create_index('idx_content_items_score_desc', 'content_items', [sa.text('score DESC')])
    op.create_index('idx_content_items_published_at_desc', 'content_items', [sa.text('published_at DESC')])
    op.create_index('idx_content_items_status', 'content_items', ['status'])
    op.create_index('idx_content_items_source_external_id', 'content_items', ['source', 'external_id'])
    op.create_index('idx_content_items_content_type', 'content_items', ['content_type'])
    op.create_index('idx_content_items_topic_seed', 'content_items', ['topic_seed'])

    # 2. Create content_item_events table
    op.create_table(
        'content_item_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('content_item_id', sa.BigInteger(), sa.ForeignKey('content_items.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    
    # Create index for content_item_events
    op.create_index('idx_content_item_events_content_item_id', 'content_item_events', ['content_item_id'])


def downgrade() -> None:
    # Drop indexes and tables in reverse order
    op.drop_index('idx_content_item_events_content_item_id', table_name='content_item_events')
    op.drop_table('content_item_events')
    
    op.drop_index('idx_content_items_topic_seed', table_name='content_items')
    op.drop_index('idx_content_items_content_type', table_name='content_items')
    op.drop_index('idx_content_items_source_external_id', table_name='content_items')
    op.drop_index('idx_content_items_status', table_name='content_items')
    op.drop_index('idx_content_items_published_at_desc', table_name='content_items')
    op.drop_index('idx_content_items_score_desc', table_name='content_items')
    op.drop_table('content_items')
