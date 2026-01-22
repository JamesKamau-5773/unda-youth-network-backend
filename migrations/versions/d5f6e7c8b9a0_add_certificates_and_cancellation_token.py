"""Add certificates table and cancellation_token to member_registrations

Revision ID: d5f6e7c8b9a0
Revises: b3a6ed533ce3
Create Date: 2026-01-22 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5f6e7c8b9a0'
down_revision = 'b3a6ed533ce3'
branch_labels = None
depends_on = None


def upgrade():
    # Add cancellation_token column to member_registrations
    op.add_column('member_registrations', sa.Column('cancellation_token', sa.String(length=64), nullable=True))
    # Create unique constraint on cancellation_token to prevent duplicates
    op.create_unique_constraint('uq_member_registrations_cancellation_token', 'member_registrations', ['cancellation_token'])

    # Create certificates table
    op.create_table(
        'certificates',
        sa.Column('certificate_id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('issued_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('pdf_data', sa.LargeBinary(), nullable=True),
        sa.Column('signature', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], name='fk_certificates_user_id', ondelete='CASCADE')
    )


def downgrade():
    # Drop certificates table
    op.drop_table('certificates')

    # Drop unique constraint and column from member_registrations
    try:
        op.drop_constraint('uq_member_registrations_cancellation_token', 'member_registrations', type_='unique')
    except Exception:
        pass
    op.drop_column('member_registrations', 'cancellation_token')
