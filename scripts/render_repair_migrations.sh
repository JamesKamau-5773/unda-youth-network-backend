#!/usr/bin/env bash
set -euo pipefail

# Safe Render repair script for aborted Alembic migration
# Usage:
#   ./scripts/render_repair_migrations.sh         # dry-run diagnostics (default)
#   ./scripts/render_repair_migrations.sh --stamp # stamp DB to revision a1b2c3d4e6f7
#   ./scripts/render_repair_migrations.sh --upgrade # attempt a controlled upgrade()

REVISION="a1b2c3d4e6f7"
PREV_REVISION="9fda0325abce"

usage() {
  cat <<EOF
Usage: $0 [--dry-run] [--stamp] [--upgrade]

This script runs diagnostics and optionally stamps or upgrades the DB.
Run in the Render Shell (or a staging copy) with the project's virtualenv active
and with the environment variable DATABASE_URL set. Always snapshot/backup
the DB before stamping or running upgrades.
EOF
}

MODE="dry"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --stamp) MODE="stamp"; shift ;;
    --upgrade) MODE="upgrade"; shift ;;
    --dry|-n) MODE="dry"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1"; usage; exit 2 ;;
  esac
done

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL not set in environment. Aborting." >&2
  exit 2
fi

echo "== DB diagnostics for revision ${REVISION} (previous ${PREV_REVISION}) =="

echo "-- Current alembic_version table contents --"
psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;" || true

echo "-- Check for candidate FK constraint names (may be absent on some DBs) --"
psql "$DATABASE_URL" -c "\
SELECT conname, conrelid::regclass::text AS table_name, pg_get_constraintdef(oid) AS definition \
FROM pg_constraint \
WHERE conname IN ('fk_users_champion_id','fk_champions_user_id','fk_users_champion','fk_champions_user');" || true

echo "-- List applied migration files (local) --"
ls -1 migrations/versions | sed -n '1,200p' || true

if [[ "$MODE" == "dry" ]]; then
  cat <<'MSG'

Dry run complete. Recommended next steps:
 - If the new FK constraints exist (see above), you can stamp the DB so Alembic records the migration as applied:
     ./scripts/render_repair_migrations.sh --stamp

 - If the constraints do not exist and DB is still at the previous revision, stamp back to previous then re-run upgrade after fixing migration:
     ./scripts/render_repair_migrations.sh --upgrade

MSG
  exit 0
fi

if [[ "$MODE" == "stamp" ]]; then
  echo "== Stamping DB to revision ${REVISION} (marks migration applied) =="
  python - <<PY
from wsgi import app
from flask_migrate import stamp
import sys
print('Running stamp(%r) inside app context...' % '${REVISION}')
with app.app_context():
    stamp('${REVISION}')
    print('Stamped to ${REVISION}')
PY
  echo "== Verify alembic_version after stamping =="
  psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;"
  exit 0
fi

if [[ "$MODE" == "upgrade" ]]; then
  echo "== Attempting controlled upgrade() inside app context (will run migrations)=="
  echo "** IMPORTANT: ensure you have a DB backup before proceeding **"
  read -p "Proceed with upgrade? Type 'yes' to continue: " confirm
  if [[ "$confirm" != "yes" ]]; then
    echo "Aborting upgrade."; exit 1
  fi

  python - <<PY
from wsgi import app
from flask_migrate import upgrade
import logging, sys
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
with app.app_context():
    print('Running upgrade()...')
    upgrade()
    print('upgrade() finished')
PY

  echo "== Verify alembic_version after upgrade =="
  psql "$DATABASE_URL" -c "SELECT * FROM alembic_version;"
  exit 0
fi

echo "Unrecognized mode: $MODE"; exit 2
