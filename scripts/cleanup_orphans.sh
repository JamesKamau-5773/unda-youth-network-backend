#!/bin/bash
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL is not set. Aborting cleanup."
  exit 1
fi

echo "Checking for orphaned FK references before cleanup..."
psql "$DATABASE_URL" -c "SELECT count(*) AS champions_orphans FROM champions WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);"
psql "$DATABASE_URL" -c "SELECT count(*) AS users_orphans FROM users WHERE champion_id IS NOT NULL AND champion_id NOT IN (SELECT id FROM champions);"

echo "Running safe cleanup (setting orphaned FK fields to NULL)..."
psql "$DATABASE_URL" <<'SQL'
BEGIN;
UPDATE champions
  SET user_id = NULL
  WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);
UPDATE users
  SET champion_id = NULL
  WHERE champion_id IS NOT NULL AND champion_id NOT IN (SELECT id FROM champions);
COMMIT;
SQL

echo "Re-checking orphan counts after cleanup..."
psql "$DATABASE_URL" -c "SELECT count(*) AS champions_orphans FROM champions WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);"
psql "$DATABASE_URL" -c "SELECT count(*) AS users_orphans FROM users WHERE champion_id IS NOT NULL AND champion_id NOT IN (SELECT id FROM champions);"

echo "Cleanup complete."
