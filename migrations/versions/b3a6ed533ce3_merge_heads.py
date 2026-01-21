"""merge heads

Revision ID: b3a6ed533ce3
Revises: a1b2c3d4e5f6, zz_add_user_frequent_pages
Create Date: 2026-01-16 17:47:15.698679

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3a6ed533ce3'
down_revision = ('a1b2c3d4e5f6', 'zz_add_user_frequent_pages')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
