"""add user level

Revision ID: 003
Revises: 002
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('level', sa.String(), nullable=False, server_default='A2'),
    )


def downgrade() -> None:
    op.drop_column('users', 'level')
