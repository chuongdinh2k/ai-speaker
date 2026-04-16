"""add deleted_at to users and topics

Revision ID: 005
Revises: 004
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('topics', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('users', 'deleted_at')
    op.drop_column('topics', 'deleted_at')
