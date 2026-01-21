# Local SQLite Fallback (development & tests)

This project supports falling back to a local SQLite database when the primary `DATABASE_URL` is unavailable.

Usage:

- Force a persistent local SQLite file (instance/local.db):

```bash
export FALLBACK_TO_SQLITE=True
unset DATABASE_URL
export DISABLE_EMAIL_IN_BUILD=True  # optional: prevent email init during startup
flask run
```

- Use in tests (in-memory SQLite is used by default when `TESTING=True`):

```bash
export DISABLE_EMAIL=True
pytest
```

Notes:
- The SQLite file is created in the `instance/` folder as `local.db`.
- `FALLBACK_TO_SQLITE=True` overrides any existing `DATABASE_URL` for local development convenience.
