"""add multilingual stt fields

Revision ID: 9c5ef8660570
Revises: fbbcc1ae10ef
Create Date: 2026-02-02 20:42:05.742800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c5ef8660570'
down_revision: Union[str, Sequence[str], None] = 'fbbcc1ae10ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    # Add preferred_languages to users table if not exists
    op.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_languages JSONB DEFAULT \'["en"]\'')
    # Add languages to notes table if not exists
    op.execute('ALTER TABLE notes ADD COLUMN IF NOT EXISTS languages JSONB DEFAULT \'[]\'')
    # Add stt_model to notes table if not exists
    op.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS stt_model VARCHAR DEFAULT 'nova'")


def downgrade() -> None:
    op.drop_column('notes', 'languages')
    op.drop_column('users', 'preferred_languages')
