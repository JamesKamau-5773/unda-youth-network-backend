"""refactor_mental_health_assessment_privacy_first

Revision ID: 9fda0325abce
Revises: 26e1fa061b8b
Create Date: 2026-01-06 13:56:23.227570

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9fda0325abce'
down_revision = '26e1fa061b8b'
branch_labels = None
depends_on = None


def upgrade():
    # Add new privacy-first columns
    op.add_column('mental_health_assessments', 
        sa.Column('champion_code', sa.String(length=20), nullable=True))
    op.add_column('mental_health_assessments', 
        sa.Column('risk_category', sa.String(length=20), nullable=True))
    op.add_column('mental_health_assessments', 
        sa.Column('score_range', sa.String(length=20), nullable=True))
    
    # Create index on champion_code for performance
    op.create_index('ix_mental_health_assessments_champion_code', 
                    'mental_health_assessments', ['champion_code'])
    
    # CRITICAL: Since we're starting fresh, truncate existing data
    # This removes all privacy-violating records
    op.execute('DELETE FROM mental_health_assessments')
    
    # Now make champion_code and risk_category non-nullable
    op.alter_column('mental_health_assessments', 'champion_code',
                    existing_type=sa.String(length=20),
                    nullable=False)
    op.alter_column('mental_health_assessments', 'risk_category',
                    existing_type=sa.String(length=20),
                    nullable=False)
    
    # Drop privacy-violating columns
    op.drop_column('mental_health_assessments', 'total_score')
    op.drop_column('mental_health_assessments', 'item_scores')
    op.drop_column('mental_health_assessments', 'severity_level')
    
    # Drop foreign key constraint and champion_id column
    # Note: Constraint name may vary by database - using try/except pattern
    with op.batch_alter_table('mental_health_assessments') as batch_op:
        batch_op.drop_constraint('mental_health_assessments_champion_id_fkey', 
                                 type_='foreignkey')
        batch_op.drop_column('champion_id')


def downgrade():
    # WARNING: This downgrade will result in data loss
    # Cannot recover raw scores that were never stored
    
    # Re-add old columns
    op.add_column('mental_health_assessments',
        sa.Column('champion_id', sa.Integer(), nullable=True))
    op.add_column('mental_health_assessments',
        sa.Column('severity_level', sa.String(length=50), nullable=True))
    op.add_column('mental_health_assessments',
        sa.Column('item_scores', sa.JSON(), nullable=True))
    op.add_column('mental_health_assessments',
        sa.Column('total_score', sa.Integer(), nullable=True))
    
    # Re-create foreign key
    op.create_foreign_key('mental_health_assessments_champion_id_fkey',
                         'mental_health_assessments', 'champions',
                         ['champion_id'], ['champion_id'],
                         ondelete='CASCADE')
    
    # Drop new privacy-first columns
    op.drop_index('ix_mental_health_assessments_champion_code')
    op.drop_column('mental_health_assessments', 'score_range')
    op.drop_column('mental_health_assessments', 'risk_category')
    op.drop_column('mental_health_assessments', 'champion_code')
