"""change podcast duration column from Integer to BigInteger

Revision ID: zzac_podcast_duration_bigint
Revises: zzab_add_user_last_login
Create Date: 2026-03-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'zzac_podcast_duration_bigint'
down_revision = 'zzab_add_user_last_login'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('podcasts', 'duration',
               existing_type=sa.Integer(),
               type_=sa.BigInteger(),
               existing_nullable=True)


def downgrade():
    op.alter_column('podcasts', 'duration',
               existing_type=sa.BigInteger(),
               type_=sa.Integer(),
               existing_nullable=True)
