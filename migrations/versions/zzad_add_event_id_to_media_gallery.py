"""Add event_id field to media_gallery for event-based album grouping.

Revision ID: zzad_add_event_id
Revises: zzac_change_podcast_duration_to_bigint
Create Date: 2026-04-09 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'zzad_add_event_id'
down_revision = 'zzac_change_podcast_duration_to_bigint'
branch_labels = None
depends_on = None


def upgrade():
    # Add event_id column to media_gallery table
    op.add_column('media_gallery', 
                  sa.Column('event_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key('fk_media_gallery_event_id', 
                         'media_gallery', 'events',
                         ['event_id'], ['event_id'],
                         ondelete='SET NULL')


def downgrade():
    # Drop foreign key
    op.drop_constraint('fk_media_gallery_event_id', 'media_gallery', type_='foreignkey')
    
    # Drop event_id column
    op.drop_column('media_gallery', 'event_id')
