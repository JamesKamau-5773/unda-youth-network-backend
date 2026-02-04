"""Add profile fields to users table: date_of_birth, gender, county_sub_county

Revision ID: 99_add_user_profile_fields
Revises: 519eca3cfb20
Create Date: 2026-02-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '99_add_user_profile_fields'
down_revision = '519eca3cfb20'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('county_sub_county', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('users', 'county_sub_county')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'date_of_birth')
