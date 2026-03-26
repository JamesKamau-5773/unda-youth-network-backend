"""add clinician integration tables and role

Revision ID: zzaa_add_clinician_integration
Revises: f6c0cddf2071
Create Date: 2026-03-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'zzaa_add_clinician_integration'
down_revision = 'f6c0cddf2071'
branch_labels = None
depends_on = None


def upgrade():
    # Create clinician_profiles table
    op.create_table(
        'clinician_profiles',
        sa.Column('clinician_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('license_number', sa.String(length=100), nullable=False),
        sa.Column('regulatory_body', sa.String(length=200), nullable=False),
        sa.Column('license_expiry_date', sa.Date(), nullable=False),
        sa.Column('professional_title', sa.String(length=100), nullable=False),
        sa.Column('professional_indemnity_insurance_provider', sa.String(length=200), nullable=False),
        sa.Column('insurance_policy_number', sa.String(length=100), nullable=True),
        sa.Column('insurance_expiry_date', sa.Date(), nullable=True),
        sa.Column('emergency_contact_name', sa.String(length=150), nullable=False),
        sa.Column('emergency_contact_phone', sa.String(length=20), nullable=False),
        sa.Column('emergency_contact_relationship', sa.String(length=50), nullable=True),
        sa.Column('years_of_practice', sa.Integer(), nullable=True),
        sa.Column('service_mode', sa.String(length=50), nullable=False),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='pending_verification'),
        sa.Column('verified_by_user_id', sa.Integer(), nullable=True),
        sa.Column('verified_date', sa.DateTime(), nullable=True),
        sa.Column('verification_notes', sa.Text(), nullable=True),
        sa.Column('declaration_accepted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('declaration_timestamp', sa.DateTime(), nullable=True),
        sa.Column('declaration_ip_address', sa.String(length=50), nullable=True),
        sa.Column('supervision_history', sa.Text(), nullable=True),
        sa.Column('supervision_provider_name', sa.String(length=150), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('account_suspended', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('suspension_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('clinician_id'),
        sa.UniqueConstraint('user_id'),
        sa.UniqueConstraint('license_number'),
    )
    op.create_index(op.f('ix_clinician_profiles_verification_status'), 'clinician_profiles', ['verification_status'], unique=False)
    op.create_index(op.f('ix_clinician_profiles_license_expiry_date'), 'clinician_profiles', ['license_expiry_date'], unique=False)

    # Create clinician_specializations table
    op.create_table(
        'clinician_specializations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinician_id', sa.Integer(), nullable=False),
        sa.Column('specialization', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['clinician_id'], ['clinician_profiles.clinician_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clinician_id', 'specialization', name='_clinician_specialization_uc'),
    )

    # Create clinician_languages table
    op.create_table(
        'clinician_languages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinician_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False),
        sa.Column('proficiency_level', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['clinician_id'], ['clinician_profiles.clinician_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('clinician_id', 'language', name='_clinician_language_uc'),
    )

    # Create clinician_audit_log table
    op.create_table(
        'clinician_audit_log',
        sa.Column('audit_id', sa.Integer(), nullable=False),
        sa.Column('clinician_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('performed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['clinician_id'], ['clinician_profiles.clinician_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['performed_by_user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('audit_id'),
    )
    op.create_index(op.f('ix_clinician_audit_log_action'), 'clinician_audit_log', ['action'], unique=False)
    op.create_index(op.f('ix_clinician_audit_log_created_at'), 'clinician_audit_log', ['created_at'], unique=False)

    # Create youth_clinician_referrals table
    op.create_table(
        'youth_clinician_referrals',
        sa.Column('referral_id', sa.Integer(), nullable=False),
        sa.Column('clinician_id', sa.Integer(), nullable=False),
        sa.Column('referring_prevention_advocate_id', sa.Integer(), nullable=True),
        sa.Column('youth_id', sa.Integer(), nullable=True),
        sa.Column('referral_date', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('referral_reason', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('completed_date', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['clinician_id'], ['clinician_profiles.clinician_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['referring_prevention_advocate_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('referral_id'),
    )

    # Create clinical_sessions table
    op.create_table(
        'clinical_sessions',
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('clinician_id', sa.Integer(), nullable=False),
        sa.Column('youth_id', sa.Integer(), nullable=True),
        sa.Column('session_date', sa.DateTime(), nullable=True),
        sa.Column('session_notes_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('risk_level', sa.String(length=50), nullable=True),
        sa.Column('follow_up_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['clinician_id'], ['clinician_profiles.clinician_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id'),
    )


def downgrade():
    op.drop_table('clinical_sessions')
    op.drop_table('youth_clinician_referrals')
    op.drop_index(op.f('ix_clinician_audit_log_created_at'), table_name='clinician_audit_log')
    op.drop_index(op.f('ix_clinician_audit_log_action'), table_name='clinician_audit_log')
    op.drop_table('clinician_audit_log')
    op.drop_table('clinician_languages')
    op.drop_table('clinician_specializations')
    op.drop_index(op.f('ix_clinician_profiles_license_expiry_date'), table_name='clinician_profiles')
    op.drop_index(op.f('ix_clinician_profiles_verification_status'), table_name='clinician_profiles')
    op.drop_table('clinician_profiles')
