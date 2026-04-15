"""add user_vocabularies table

Revision ID: 002
Revises: 001
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'user_vocabularies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('topic_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('topics.id'), nullable=False),
        sa.Column('word', sa.String(), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.create_index('ix_user_vocabularies_user_topic', 'user_vocabularies', ['user_id', 'topic_id'])

def downgrade() -> None:
    op.drop_index('ix_user_vocabularies_user_topic', table_name='user_vocabularies')
    op.drop_table('user_vocabularies')
