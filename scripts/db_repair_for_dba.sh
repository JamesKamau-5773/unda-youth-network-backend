#!/usr/bin/env bash
set -euo pipefail

# DBA-facing non-interactive repair script for aborted Alembic migration
# Usage (examples):
#   # Dry run (diagnostics only)
#   ./scripts/db_repair_for_dba.sh --dry-run
#
#   # Stamp DB to migration (only if FK constraints already exist):
#   ./scripts/db_repair_for_dba.sh --stamp
#
#   # Attempt non-interactive upgrade (requires --force):
#   ./scripts/db_repair_for_dba.sh --upgrade --force
#
# This script is intended to be run by a DBA or CI runner that has network
# access to the Postgres instance and can run the project's Python code.
# It will not perform destructive manual SQL changes; stamping only marks the
# migration as applied in Alembic when schema changes are already present.

REVISION="a1b2c3d4e6f7"
PREV_REVISION="9fda0325abce"

usage(){
  cat <<EOF
Usage: $0 [--dry-run] [--stamp] [--upgrade --force]

Flags:
  --dry-run    Print diagnostics and exit (default)
  --stamp      Mark migration ${REVISION} as applied (only if checks pass)
  --upgrade    Run `upgrade()` inside the app context (non-interactive)
  --force      Required with --upgrade to avoid accidental runs

Environment:
  DATABASE_URL must be set (Postgres connection string)
  Run from project root with a Python virtualenv that can import the app.

EOF
}

MODE="dry"
FORCE="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) MODE="dry"; shift;;
    --stamp) MODE="stamp"; shift;;
    --upgrade) MODE="upgrade"; shift;;
    --force) FORCE="true"; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 2;;
  esac
done

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL not set. Set it and re-run." >&2
  exit 2
fi

echo "== Diagnostics for migration ${REVISION} =="

echo "-- alembic_version table --"
psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;" || true

echo "-- Check for FK constraint names --"
psql "$DATABASE_URL" -c "\
SELECT conname, conrelid::regclass::text AS table_name, pg_get_constraintdef(oid) AS definition \
FROM pg_constraint \
WHERE conname IN ('fk_users_champion_id','fk_champions_user_id','fk_users_champion','fk_champions_user');" || true

echo "-- Completed diagnostics --"

if [[ "$MODE" == "dry" ]]; then
  echo "Dry run finished. Review output. Use --stamp if constraints exist or --upgrade --force to run migrations.";
  exit 0
fi
# Helper: check if new FK constraints exist
constraints_exist(){
  local cnt
  cnt=$(psql "$DATABASE_URL" -t -c "\
SELECT count(*) FROM pg_constraint WHERE conname IN ('fk_users_champion_id','fk_champions_user_id');" | tr -d '[:space:]' || true)
  if [[ -z "$cnt" ]]; then
    cnt=0
  fi
  if [[ "$cnt" -ge 1 ]]; then
    return 0
  fi
  return 1
}

if [[ "$MODE" == "stamp" ]]; then
  echo "Running pre-stamp checks..."
  if constraints_exist; then
    echo "Detected new FK constraints. Proceeding to stamp alembic revision ${REVISION}."
    python - <<PY
from wsgi import app
from flask_migrate import stamp
with app.app_context():
    stamp('${REVISION}')
    print('Stamped to ${REVISION}')
PY
    echo "Verify alembic_version:"
    psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;"
    exit 0
  else
    echo "New FK constraints not detected; aborting stamp. Run --dry-run and investigate." >&2
    exit 3
  fi
fi

if [[ "$MODE" == "upgrade" ]]; then
  if [[ "$FORCE" != "true" ]]; then
    echo "--upgrade requires --force to run non-interactively. Aborting." >&2
    exit 2
  fi
  echo "Proceeding to run upgrade() inside app context (non-interactive)."
  python - <<PY
from wsgi import app
from flask_migrate import upgrade
import logging, sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
with app.app_context():
    upgrade()
    print('upgrade() finished')
PY
  echo "Verify alembic_version:"
  psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;"
  exit 0
fi

echo "Unhandled mode: $MODE"; exit 2
