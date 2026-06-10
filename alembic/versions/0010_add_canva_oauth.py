"""add_canva_oauth

Revision ID: 0010_canva_oauth
Revises: 0009_canva_only
Create Date: 2026-06-10 04:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_canva_oauth"
down_revision: Union[str, Sequence[str], None] = "0009_canva_only"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canva_oauth_states",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("state", sa.Text(), nullable=False, unique=True),
        sa.Column("code_verifier", sa.Text(), nullable=False),
        sa.Column("redirect_after", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )
    op.create_index("idx_canva_oauth_states_state", "canva_oauth_states", ["state"])
    op.create_index("idx_canva_oauth_states_expires_at", "canva_oauth_states", ["expires_at"])

    op.create_table(
        "canva_oauth_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("provider", sa.Text(), nullable=False, server_default="canva"),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_type", sa.Text(), nullable=False, server_default="Bearer"),
        sa.Column("scopes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.UniqueConstraint("provider", name="uq_canva_oauth_tokens_provider"),
        sa.CheckConstraint("provider = 'canva'", name="check_canva_oauth_tokens_provider"),
    )
    op.create_index("idx_canva_oauth_tokens_provider", "canva_oauth_tokens", ["provider"])


def downgrade() -> None:
    op.drop_index("idx_canva_oauth_tokens_provider", table_name="canva_oauth_tokens")
    op.drop_table("canva_oauth_tokens")
    op.drop_index("idx_canva_oauth_states_expires_at", table_name="canva_oauth_states")
    op.drop_index("idx_canva_oauth_states_state", table_name="canva_oauth_states")
    op.drop_table("canva_oauth_states")
