"""add_search_configs_and_runs

Revision ID: 0003_add_search_configs_and_runs
Revises: 0002_add_status_check_constraint
Create Date: 2026-06-05 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003_add_search_configs_and_runs'
down_revision: Union[str, Sequence[str], None] = '0002_add_status_check_constraint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create search_configs table
    op.create_table(
        'search_configs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='active'),
        sa.Column('language', sa.Text(), nullable=True, server_default='pt'),
        sa.Column('country_code', sa.Text(), nullable=True, server_default='BR'),
        sa.Column('region_code', sa.Text(), nullable=True),
        sa.Column('days_back', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('min_views', sa.BigInteger(), nullable=True, server_default='30000'),
        sa.Column('max_results_per_query', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('sources_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='["youtube", "google_news"]'),
        sa.Column('keywords_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('negative_keywords_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('youtube_categories_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )
    
    # Check constraint for search_configs status
    op.create_check_constraint(
        constraint_name="check_search_configs_status",
        table_name="search_configs",
        condition="status IN ('active', 'paused', 'archived')"
    )
    
    # Indexes for search_configs
    op.create_index('idx_search_configs_status', 'search_configs', ['status'])
    op.create_index('idx_search_configs_name', 'search_configs', ['name'])

    # 2. Create search_runs table
    op.create_table(
        'search_runs',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('search_config_id', sa.BigInteger(), sa.ForeignKey('search_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='queued'),
        sa.Column('trigger_source', sa.Text(), nullable=True, server_default='manual'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('items_found', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_inserted', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_updated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('raw_summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()'))
    )
    
    # Check constraint for search_runs status
    op.create_check_constraint(
        constraint_name="check_search_runs_status",
        table_name="search_runs",
        condition="status IN ('queued', 'running', 'completed', 'failed')"
    )

    # Indexes for search_runs
    op.create_index('idx_search_runs_search_config_id', 'search_runs', ['search_config_id'])
    op.create_index('idx_search_runs_status', 'search_runs', ['status'])
    op.create_index('idx_search_runs_created_at_desc', 'search_runs', [sa.text('created_at DESC')])

    # 3. Add foreign keys to content_items
    op.add_column('content_items', sa.Column('search_config_id', sa.BigInteger(), sa.ForeignKey('search_configs.id', ondelete='SET NULL'), nullable=True))
    op.add_column('content_items', sa.Column('search_run_id', sa.BigInteger(), sa.ForeignKey('search_runs.id', ondelete='SET NULL'), nullable=True))
    
    # Add indexes for these fields on content_items for search optimization
    op.create_index('idx_content_items_search_config_id', 'content_items', ['search_config_id'])
    op.create_index('idx_content_items_search_run_id', 'content_items', ['search_run_id'])


def downgrade() -> None:
    # Drop indexes from content_items
    op.drop_index('idx_content_items_search_run_id', table_name='content_items')
    op.drop_index('idx_content_items_search_config_id', table_name='content_items')
    
    # Drop columns from content_items
    op.drop_column('content_items', 'search_run_id')
    op.drop_column('content_items', 'search_config_id')
    
    # Drop search_runs table
    op.drop_index('idx_search_runs_created_at_desc', table_name='search_runs')
    op.drop_index('idx_search_runs_status', table_name='search_runs')
    op.drop_index('idx_search_runs_search_config_id', table_name='search_runs')
    op.drop_constraint("check_search_runs_status", "search_runs", type_="check")
    op.drop_table('search_runs')
    
    # Drop search_configs table
    op.drop_index('idx_search_configs_name', table_name='search_configs')
    op.drop_index('idx_search_configs_status', table_name='search_configs')
    op.drop_constraint("check_search_configs_status", "search_configs", type_="check")
    op.drop_table('search_configs')
