#!/usr/bin/env bash
set -euo pipefail

# Run migrations with a Postgres advisory lock so only one process upgrades at a time.
# Expects DATABASE_URL in the environment.

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL must be set" >&2
  exit 2
fi

LOCK_KEY=${MIGRATION_ADVISORY_LOCK_KEY:-1234567890}

echo "Acquiring advisory lock ${LOCK_KEY}..."
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT pg_advisory_lock(${LOCK_KEY});"

trap 'psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "SELECT pg_advisory_unlock(${LOCK_KEY})" || true' EXIT

echo "Running migrations (flask db upgrade)..."
if ! flask db upgrade; then
  echo "MIGRATIONS FAILED" >&2
  # If SENTRY_DSN is provided, send a simple alert
  if [ -n "${SENTRY_DSN:-}" ]; then
    python - <<'PY'
import os
try:
    import sentry_sdk
    sentry_sdk.init(os.environ['SENTRY_DSN'])
    sentry_sdk.capture_message('Migration failed during run_migrations.sh')
except Exception:
    pass
PY
  fi
  exit 1
fi

echo "Migrations completed successfully."
