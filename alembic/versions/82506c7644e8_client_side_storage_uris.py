"""client_side_storage_uris

Revision ID: 82506c7644e8
Revises: 27a3b82897cf
Create Date: 2026-02-03 04:15:31.241765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82506c7644e8'
down_revision: Union[str, Sequence[str], None] = '27a3b82897cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
