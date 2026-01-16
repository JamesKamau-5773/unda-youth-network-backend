from alembic import op
from sqlalchemy import text


def constraint_exists(conn, name: str) -> bool:
    """Return True if a constraint with the given name exists in the DB."""
    res = conn.execute(text("SELECT 1 FROM pg_constraint WHERE conname = :name"), {"name": name}).scalar()
    return bool(res)


def add_fk_not_valid_and_validate(conn, table: str, constraint_name: str, column: str, ref_table: str, ref_column: str) -> bool:
    """
    Add a foreign-key constraint `constraint_name` on `table(column)` referencing
    `ref_table(ref_column)` using NOT VALID then VALIDATE pattern.

    Returns True if the constraint was created (or validated), False if it already existed.
    Raises on unexpected errors.
    """
    if constraint_exists(conn, constraint_name):
        return False

    try:
        # Run the DDL in its own transaction so a single statement failure doesn't abort an outer transaction
        with op.get_context().autocommit_block():
            conn.execute(text(f"""
                ALTER TABLE {table}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({column})
                REFERENCES {ref_table}({ref_column})
                NOT VALID;
            """))

        # Validate - may still fail if orphan rows exist; caller can handle exceptions
        conn.execute(text(f"ALTER TABLE {table} VALIDATE CONSTRAINT {constraint_name};"))
        return True
    except Exception:
        # Let the caller handle/raise; keep this helper minimal
        raise
