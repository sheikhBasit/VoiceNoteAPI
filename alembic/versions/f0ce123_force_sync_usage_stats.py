"""force_sync_usage_stats_column

Revision ID: f0ce123_force
Revises: e6d06eb4f606
Create Date: 2026-02-01 02:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f0ce123_force'
down_revision: Union[str, Sequence[str], None] = 'e6d06eb4f606'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Forcefully add usage_stats using native PG syntax to resolve production sync issue."""
    # Using raw SQL with IF NOT EXISTS to guarantee column existence without relying on inspector state
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS usage_stats JSONB DEFAULT '{}'::jsonb"
    )

def downgrade() -> None:
    """Drop the column if needed."""
    op.drop_column('users', 'usage_stats')
