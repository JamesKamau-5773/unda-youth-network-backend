"""Merge event submission and programs migrations

Revision ID: d42c4ad8c236
Revises: 
Create Date: 2026-02-12 19:01:13.747721

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd42c4ad8c236'
down_revision = ('add_event_submission_tracking', 'bb2c3d4e5f6')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
