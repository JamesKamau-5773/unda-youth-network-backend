"""add last_login timestamp field to users

Revision ID: zzab_add_user_last_login
Revises: zzaa_add_clinician_integration
Create Date: 2026-03-26 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'zzab_add_user_last_login'
down_revision = 'zzaa_add_clinician_integration'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'last_login')
