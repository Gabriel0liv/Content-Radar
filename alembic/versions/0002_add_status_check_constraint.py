"""add_status_check_constraint

Revision ID: 0002_add_status_check_constraint
Revises: 0001_baseline
Create Date: 2026-06-04 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_add_status_check_constraint'
down_revision: Union[str, Sequence[str], None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add check constraint for status column
    op.create_check_constraint(
        constraint_name="check_content_items_status",
        table_name="content_items",
        condition="status IN ('new', 'reviewed', 'selected', 'rejected', 'produced', 'archived')"
    )


def downgrade() -> None:
    # Drop check constraint for status column
    op.drop_constraint(
        constraint_name="check_content_items_status",
        table_name="content_items",
        type_="check"
    )
