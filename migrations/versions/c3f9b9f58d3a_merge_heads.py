"""Merge migration to combine multiple heads into a single head.

Revision ID: c3f9b9f58d3a
Revises: 22bb190d9436, a1b2c3d4e6f7
Create Date: 2026-01-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3f9b9f58d3a'
down_revision = ('22bb190d9436', 'a1b2c3d4e6f7')
branch_labels = None
depends_on = None


def upgrade():
    # Merge migration: no schema changes required; this revision
    # simply consolidates multiple heads into a single head so
    # that `alembic upgrade` can proceed cleanly.
    pass


def downgrade():
    # Downgrade would be non-trivial (splitting heads). Leave as no-op.
    pass
