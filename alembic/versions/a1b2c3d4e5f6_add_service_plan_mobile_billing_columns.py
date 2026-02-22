"""add service plan mobile billing columns

Revision ID: a1b2c3d4e5f6
Revises: 4803618194b2
Create Date: 2026-02-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '4803618194b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('service_plans', sa.Column('google_play_product_id', sa.String(), nullable=True))
    op.add_column('service_plans', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('service_plans', sa.Column('monthly_note_limit', sa.Integer(), server_default='10', nullable=True))
    op.add_column('service_plans', sa.Column('monthly_task_limit', sa.Integer(), server_default='20', nullable=True))
    op.add_column('service_plans', sa.Column('features', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('service_plans', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True))


def downgrade() -> None:
    op.drop_column('service_plans', 'is_active')
    op.drop_column('service_plans', 'features')
    op.drop_column('service_plans', 'monthly_task_limit')
    op.drop_column('service_plans', 'monthly_note_limit')
    op.drop_column('service_plans', 'description')
    op.drop_column('service_plans', 'google_play_product_id')
