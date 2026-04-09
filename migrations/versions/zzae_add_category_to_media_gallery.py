"""add category field to media_gallery for user-defined grouping

Revision ID: zzae_add_category_to_media_gallery
Revises: zzad_add_event_id
Create Date: 2026-04-09 10:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'zzae_add_category_to_media_gallery'
down_revision = 'zzad_add_event_id'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('media_gallery', sa.Column('category', sa.String(length=100), nullable=True))


def downgrade():
    op.drop_column('media_gallery', 'category')
