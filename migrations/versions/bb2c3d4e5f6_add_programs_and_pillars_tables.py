"""add programs and pillars tables

Revision ID: bb2c3d4e5f6
Revises: aa1b2c3d4e5
Create Date: 2026-02-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bb2c3d4e5f6'
down_revision = 'aa1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    # Create programs table
    op.create_table(
        'programs',
        sa.Column('program_id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False, unique=True),
        sa.Column('tagline', sa.String(length=200), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('link', sa.String(length=100), nullable=True),
        sa.Column('cta', sa.String(length=50), nullable=True, server_default='Learn More'),
        sa.Column('highlights', sa.JSON(), nullable=True),
        sa.Column('featured', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('published', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
    )

    # Create pillars table
    op.create_table(
        'pillars',
        sa.Column('pillar_id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(length=50), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False, unique=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table('pillars')
    op.drop_table('programs')
