"""add_invite_token_fields

Revision ID: f4b5c6d7e8a9
Revises: d1f2e3c4b5a6
Create Date: 2026-01-16 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4b5c6d7e8a9'
down_revision = 'd1f2e3c4b5a6'
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable invite token fields to users table
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('invite_token', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('invite_token_expires', sa.DateTime(), nullable=True))


def downgrade():
    # Remove invite token fields
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('invite_token_expires')
        batch_op.drop_column('invite_token')
