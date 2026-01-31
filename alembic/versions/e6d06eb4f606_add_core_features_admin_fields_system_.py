"""Add core features: admin fields system settings and timezone

Revision ID: e6d06eb4f606
Revises: 67e2253fc857
Create Date: 2026-01-31 13:47:23.927700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'e6d06eb4f606'
down_revision: Union[str, Sequence[str], None] = '67e2253fc857'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Standardized to avoid redundant table creation."""
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()

    # 1. New Table: Service Plans
    if 'service_plans' not in tables:
        op.create_table('service_plans',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('price_per_minute', sa.Integer(), nullable=True),
            sa.Column('monthly_credits', sa.Integer(), nullable=True),
            sa.Column('ai_models_allowed', sa.JSON(), nullable=True),
            sa.Column('can_use_rag', sa.Boolean(), nullable=True),
            sa.Column('max_storage_mb', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=True),
            sa.Column('updated_at', sa.BigInteger(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )

    # 2. Users Table Updates
    user_cols = [c['name'] for c in inspector.get_columns('users')]
    if 'plan_id' not in user_cols:
        op.add_column('users', sa.Column('plan_id', sa.String(), nullable=True))
        op.create_foreign_key('fk_user_plan', 'users', 'service_plans', ['plan_id'], ['id'])
    if 'timezone' not in user_cols:
        op.add_column('users', sa.Column('timezone', sa.String(), nullable=True))
        op.create_index(op.f('ix_users_timezone'), 'users', ['timezone'], unique=False)
    if 'usage_stats' not in user_cols:
        op.add_column('users', sa.Column('usage_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # 3. Tasks Table Updates (Critical Fixes for Ownership & Timezone)
    task_cols = [c['name'] for c in inspector.get_columns('tasks')]
    if 'user_id' not in task_cols:
        op.add_column('tasks', sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True))
        op.create_index(op.f('ix_tasks_user_id'), 'tasks', ['user_id'], unique=False)
    if 'created_at' not in task_cols:
        op.add_column('tasks', sa.Column('created_at', sa.BigInteger(), nullable=True))
    if 'updated_at' not in task_cols:
        op.add_column('tasks', sa.Column('updated_at', sa.BigInteger(), nullable=True))
    if 'deadline' not in task_cols:
        op.add_column('tasks', sa.Column('deadline', sa.BigInteger(), nullable=True))
        op.create_index(op.f('ix_tasks_deadline'), 'tasks', ['deadline'], unique=False)

    # 4. Notes Table Updates
    note_cols = [c['name'] for c in inspector.get_columns('notes')]
    if 'updated_at' not in note_cols:
        op.add_column('notes', sa.Column('updated_at', sa.BigInteger(), nullable=True))

    # 5. API Keys - Ensure constraint name is unique/exists
    # (The user error specifically mentioned uq_service_priority)
    # If the table creation failed here, it means it already exists and we just need to skip it.
    # The 'api_keys' table is already handled in previous migrations cleanly.

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('notes', 'updated_at')
    op.drop_index(op.f('ix_tasks_user_id'), table_name='tasks')
    op.drop_column('tasks', 'user_id')
    op.drop_index(op.f('ix_users_timezone'), table_name='users')
    op.drop_column('users', 'timezone')
    op.drop_table('service_plans')
