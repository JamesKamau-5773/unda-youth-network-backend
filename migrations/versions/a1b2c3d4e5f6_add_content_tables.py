"""add content tables: media_gallery, institutional_toolkit, umv_global, resources

Revision ID: a1b2c3d4e5f6
Revises: f4b5c6d7e8a9
Create Date: 2026-01-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f4b5c6d7e8a9'
branch_labels = None
deploy_revision = None


def upgrade():
    op.create_table(
        'media_gallery',
        sa.Column('gallery_id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('media_items', sa.JSON(), nullable=True),
        sa.Column('featured_media', sa.String(length=500), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'institutional_toolkit',
        sa.Column('item_id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'umv_global',
        sa.Column('entry_id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(length=255), nullable=False, unique=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'resources',
        sa.Column('resource_id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1000), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('resources')
    op.drop_table('umv_global')
    op.drop_table('institutional_toolkit')
    op.drop_table('media_gallery')
