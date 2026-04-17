"""add conversation context columns

Revision ID: 006
Revises: 005
Create Date: 2026-04-17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('conversations', sa.Column('user_context', JSONB, nullable=True))
    op.add_column('conversations', sa.Column('conversation_prompt', sa.Text, nullable=True))


def downgrade():
    op.drop_column('conversations', 'conversation_prompt')
    op.drop_column('conversations', 'user_context')
