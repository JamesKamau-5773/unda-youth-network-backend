"""Add refresh_tokens table for rotating and revoking refresh tokens.

Revision ID: f7e6d5c4b3a2
Revises: c3f9b9f58d3a
Create Date: 2026-01-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'f7e6d5c4b3a2'
down_revision = 'c3f9b9f58d3a'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'refresh_tokens' not in inspector.get_table_names():
        op.create_table(
            'refresh_tokens',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
            sa.Column('token_hash', sa.String(length=128), nullable=False),
            sa.Column('jti', sa.String(length=100), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
            sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        )
        op.create_index(op.f('ix_refresh_tokens_jti'), 'refresh_tokens', ['jti'], unique=False)
        op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'refresh_tokens' in inspector.get_table_names():
        # Drop indexes if they exist
        try:
            op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
        except Exception:
            pass
        try:
            op.drop_index(op.f('ix_refresh_tokens_jti'), table_name='refresh_tokens')
        except Exception:
            pass
        op.drop_table('refresh_tokens')
