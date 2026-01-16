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
# Capture logs to a temp file so we can send them to Sentry on failure
LOGFILE=${MIGRATION_LOGFILE:-/tmp/migration.log}
rm -f "$LOGFILE"
set -o pipefail
if ! (flask db upgrade 2>&1 | tee "$LOGFILE"); then
  echo "MIGRATIONS FAILED" >&2
  if [ -n "${SENTRY_DSN:-}" ]; then
    # Send last part of the log to Sentry to provide context
    tail -c 2000 "$LOGFILE" > "${LOGFILE}.snippet" || cp "$LOGFILE" "${LOGFILE}.snippet" 2>/dev/null || true
    python - <<'PY'
import os
import sentry_sdk
from sentry_sdk import capture_message
dsn = os.environ.get('SENTRY_DSN')
try:
    sentry_sdk.init(dsn)
    with open(os.environ.get('MIGRATION_LOGFILE', '/tmp/migration.log') + '.snippet', 'r') as f:
        snippet = f.read()
    capture_message('Migration failed during run_migrations.sh: ' + snippet)
except Exception:
    pass
PY
  fi
  echo "See $LOGFILE for full output" >&2
  exit 1
fi

echo "Migrations completed successfully."
