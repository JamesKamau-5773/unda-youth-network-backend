"""rename_champion_role_to_prevention_advocate

Revision ID: 26e1fa061b8b
Revises: 709cd9ae632d
Create Date: 2026-01-06 13:51:51.917346

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26e1fa061b8b'
down_revision = '709cd9ae632d'
branch_labels = None
depends_on = None


def upgrade():
    # Update all users with 'Champion' role to 'Prevention Advocate'
    op.execute("""
        UPDATE users 
        SET role = 'Prevention Advocate' 
        WHERE role = 'Champion'
    """)


def downgrade():
    # Rollback: Change 'Prevention Advocate' back to 'Champion'
    op.execute("""
        UPDATE users 
        SET role = 'Champion' 
        WHERE role = 'Prevention Advocate'
    """)
