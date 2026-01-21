"""add frequent_pages json column to users

Revision ID: zz_add_user_frequent_pages
Revises: 
Create Date: 2026-01-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'zz_add_user_frequent_pages'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('frequent_pages', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('users', 'frequent_pages')
