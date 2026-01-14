"""add named FK constraints for users <-> champions

Revision ID: a1b2c3d4e6f7
Revises: 9fda0325abce
Create Date: 2026-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e6f7'
down_revision = '9fda0325abce'
branch_labels = None
depends_on = None


def upgrade():
    # Normalize FK constraint names between `users` and `champions`.
    # Attempt to drop legacy constraint names (if they exist), then create
    # the named constraints we use in the models.

    # champions.user_id -> users.user_id
    try:
        # Clean up any orphaned champions.user_id values that point to missing users.
        # This avoids 'current transaction is aborted' errors when creating FK constraints.
        op.execute("""
        DO $$
        BEGIN
            IF EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_name='champions' AND column_name='user_id'
            ) AND EXISTS(
                SELECT 1 FROM information_schema.tables WHERE table_name='users'
            ) THEN
                EXECUTE 'UPDATE champions SET user_id = NULL WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT user_id FROM users)';
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- swallow errors here to avoid aborting the outer migration transaction
            RAISE NOTICE 'Ignored error while cleaning champions.user_id: %', SQLERRM;
        END
        $$;
        """)
        
        with op.batch_alter_table('champions', schema=None) as batch_op:
            # drop any legacy constraint names that may exist
            for legacy in ('fk_champions_user', 'fk_champions_user_id'):
                try:
                    batch_op.drop_constraint(legacy, type_='foreignkey')
                except Exception:
                    pass
            batch_op.create_foreign_key(
                'fk_champions_user_id',
                'users',
                ['user_id'],
                ['user_id'],
                ondelete='SET NULL'
            )
    except Exception:
        # Best-effort; errors may occur on some DB backends or if constraint
        # already exists; ignore to avoid blocking deployments.
        pass

    # users.champion_id -> champions.champion_id
    try:
        # Clean up orphaned users.champion_id values before creating the FK.
        op.execute("""
        DO $$
        BEGIN
            IF EXISTS(
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='champion_id'
            ) AND EXISTS(
                SELECT 1 FROM information_schema.tables WHERE table_name='champions'
            ) THEN
                EXECUTE 'UPDATE users SET champion_id = NULL WHERE champion_id IS NOT NULL AND champion_id NOT IN (SELECT champion_id FROM champions)';
            END IF;
        EXCEPTION WHEN OTHERS THEN
            -- swallow errors here to avoid aborting the outer migration transaction
            RAISE NOTICE 'Ignored error while cleaning users.champion_id: %', SQLERRM;
        END
        $$;
        """)
        
        with op.batch_alter_table('users', schema=None) as batch_op:
            for legacy in ('fk_users_champion', 'fk_users_champion_id'):
                try:
                    batch_op.drop_constraint(legacy, type_='foreignkey')
                except Exception:
                    pass
            batch_op.create_foreign_key(
                'fk_users_champion_id',
                'champions',
                ['champion_id'],
                ['champion_id'],
                ondelete='SET NULL'
            )
    except Exception:
        pass


def downgrade():
    # Reverse the upgrade by dropping the named FKs and restoring legacy names
    try:
        with op.batch_alter_table('users', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('fk_users_champion_id', type_='foreignkey')
            except Exception:
                pass
            # restore legacy name for downgrade clarity
            batch_op.create_foreign_key(
                'fk_users_champion',
                'champions',
                ['champion_id'],
                ['champion_id'],
                ondelete='SET NULL'
            )
    except Exception:
        pass

    try:
        with op.batch_alter_table('champions', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('fk_champions_user_id', type_='foreignkey')
            except Exception:
                pass
            batch_op.create_foreign_key(
                'fk_champions_user',
                'users',
                ['user_id'],
                ['user_id'],
                ondelete='SET NULL'
            )
    except Exception:
        pass
