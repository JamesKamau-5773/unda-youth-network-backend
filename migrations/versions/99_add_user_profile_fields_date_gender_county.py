depends_on = None
def downgrade():
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
    bind = op.get_bind()
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date_of_birth', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('gender', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('county_sub_county', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('county_sub_county')
        batch_op.drop_column('gender')
        batch_op.drop_column('date_of_birth')
