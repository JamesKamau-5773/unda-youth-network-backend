"""Add champion health and risk fields

Revision ID: aa1b2c3d4e5
Revises: 99_add_user_profile_fields,6f0e1bb57cb2
Create Date: 2026-02-04 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'aa1b2c3d4e5'
# This migration follows multiple heads that were merged/applied; include both as down revisions
down_revision = ('99_add_user_profile_fields','6f0e1bb57cb2')
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    existing = set(r[0] for r in conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='champions'")))
    with op.batch_alter_table('champions', schema=None) as batch_op:
        if 'medical_conditions' not in existing:
            batch_op.add_column(sa.Column('medical_conditions', sa.Text(), nullable=True))
        if 'allergies' not in existing:
            batch_op.add_column(sa.Column('allergies', sa.Text(), nullable=True))
        if 'mental_health_support' not in existing:
            batch_op.add_column(sa.Column('mental_health_support', sa.Text(), nullable=True))
        if 'disabilities' not in existing:
            batch_op.add_column(sa.Column('disabilities', sa.Text(), nullable=True))
        if 'medication_required' not in existing:
            batch_op.add_column(sa.Column('medication_required', sa.Text(), nullable=True))
        if 'dietary_requirements' not in existing:
            batch_op.add_column(sa.Column('dietary_requirements', sa.Text(), nullable=True))
        if 'health_notes' not in existing:
            batch_op.add_column(sa.Column('health_notes', sa.Text(), nullable=True))
        if 'risk_level' not in existing:
            batch_op.add_column(sa.Column('risk_level', sa.String(length=20), nullable=True, server_default='Low'))
        if 'risk_assessment_date' not in existing:
            batch_op.add_column(sa.Column('risk_assessment_date', sa.Date(), nullable=True))
        if 'risk_notes' not in existing:
            batch_op.add_column(sa.Column('risk_notes', sa.Text(), nullable=True))
        if 'last_contact_date' not in existing:
            batch_op.add_column(sa.Column('last_contact_date', sa.Date(), nullable=True))
        if 'next_review_date' not in existing:
            batch_op.add_column(sa.Column('next_review_date', sa.Date(), nullable=True))


def downgrade():
    with op.batch_alter_table('champions', schema=None) as batch_op:
        batch_op.drop_column('next_review_date')
        batch_op.drop_column('last_contact_date')
        batch_op.drop_column('risk_notes')
        batch_op.drop_column('risk_assessment_date')
        batch_op.drop_column('risk_level')
        batch_op.drop_column('health_notes')
        batch_op.drop_column('dietary_requirements')
        batch_op.drop_column('medication_required')
        batch_op.drop_column('disabilities')
        batch_op.drop_column('mental_health_support')
        batch_op.drop_column('allergies')
        batch_op.drop_column('medical_conditions')
