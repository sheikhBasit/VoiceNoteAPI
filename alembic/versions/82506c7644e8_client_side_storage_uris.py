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
    # Renames for Note table (Safely)
    op.execute("""
        DO $$ 
        BEGIN 
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='notes' AND column_name='document_urls') THEN
                ALTER TABLE notes RENAME COLUMN document_urls TO document_uris;
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS image_uris JSONB DEFAULT '[]'")
    
    # Renames for Task table (Safely)
    op.execute("""
        DO $$ 
        BEGIN 
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='image_urls') THEN
                ALTER TABLE tasks RENAME COLUMN image_urls TO image_uris;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tasks' AND column_name='document_urls') THEN
                ALTER TABLE tasks RENAME COLUMN document_urls TO document_uris;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE notes RENAME COLUMN document_uris TO document_urls")
    op.drop_column('notes', 'image_uris')
    
    op.execute("ALTER TABLE tasks RENAME COLUMN image_uris TO image_urls")
    op.execute("ALTER TABLE tasks RENAME COLUMN document_uris TO document_urls")
