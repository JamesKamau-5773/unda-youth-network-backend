"""make_emails_nullable

Revision ID: d1f2e3c4b5a6
Revises: c3f9b9f58d3a
Create Date: 2026-01-16 13:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1f2e3c4b5a6'
down_revision = 'c3f9b9f58d3a'
branch_labels = None
depends_on = None


def upgrade():
    # Make email columns nullable where they were previously NOT NULL.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=True)

    with op.batch_alter_table('champions', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=True)

    with op.batch_alter_table('member_registrations', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=True)

    with op.batch_alter_table('champion_applications', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=True)

    with op.batch_alter_table('seed_funding_applications', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=True)


def downgrade():
    # Revert email columns to NOT NULL. This may fail if NULL values exist.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=False)

    with op.batch_alter_table('champions', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=False)

    with op.batch_alter_table('member_registrations', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=False)

    with op.batch_alter_table('champion_applications', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=False)

    with op.batch_alter_table('seed_funding_applications', schema=None) as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=100), nullable=False)
