#!/usr/bin/env bash
set -euo pipefail

# Idempotent script to make email columns nullable in the database.
# Usage: DATABASE_URL=<url> ./scripts/make_emails_nullable.sh

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL must be set"
  exit 2
fi

SQL="\
ALTER TABLE IF EXISTS users ALTER COLUMN email DROP NOT NULL;
ALTER TABLE IF EXISTS champions ALTER COLUMN email DROP NOT NULL;
ALTER TABLE IF EXISTS member_registrations ALTER COLUMN email DROP NOT NULL;
ALTER TABLE IF EXISTS champion_applications ALTER COLUMN email DROP NOT NULL;
ALTER TABLE IF EXISTS seed_funding_applications ALTER COLUMN email DROP NOT NULL;
"

echo "Applying email NULLability changes..."
# Run via psql; allow this to fail fast so operator sees errors
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -c "$SQL"

echo "Done." 
