"""add_guest_to_subscriptiontier

Revision ID: add_guest_enum
Revises: 82506c7644e8
Create Date: 2026-02-04 23:52:55.936384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_guest_enum'
down_revision: Union[str, Sequence[str], None] = '82506c7644e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Adding 'GUEST' to subscriptiontier enum
    # We use execute here because sa.Enum doesn't support ALTER TYPE ADD VALUE directly in a convenient way across all DB versions in Alembic
    # The 'commit' and 'IF NOT EXISTS' are specific to how Postgres handles enum changes.
    op.execute("ALTER TYPE subscriptiontier ADD VALUE IF NOT EXISTS 'GUEST'")


def downgrade() -> None:
    """Downgrade schema."""
    # Downgrading enums in Postgres is not straightforward and often not supported without dropping/recreating.
    pass
