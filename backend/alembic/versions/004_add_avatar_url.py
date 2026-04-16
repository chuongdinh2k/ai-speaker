"""add avatar_url to users

Revision ID: 004
Revises: 003
Create Date: 2026-04-16

"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('avatar_url', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
