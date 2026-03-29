#!/bin/sh
# Auto-migration script — runs inside the backend container on every deploy.
# Tracks applied migrations in schema_migrations table.
# Safe to run multiple times — skips already-applied migrations.

set -e

DATABASE_URL="${DATABASE_URL}"

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL is not set"
  exit 1
fi

echo "=== ApplyPilot Migrations ==="

# Create tracking table if it doesn't exist
psql "$DATABASE_URL" -c "
  CREATE TABLE IF NOT EXISTS schema_migrations (
    version    TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
  );
"

MIGRATIONS_DIR="/app/migrations"

# Loop through all .up.sql files in order
for filepath in $(ls "$MIGRATIONS_DIR"/*.up.sql | sort); do
  filename=$(basename "$filepath")
  version="${filename%.up.sql}"

  # Check if already applied
  count=$(psql "$DATABASE_URL" -tAc "SELECT COUNT(*) FROM schema_migrations WHERE version = '$version'")

  if [ "$count" -eq "1" ]; then
    echo "  [skip] $version (already applied)"
  else
    echo "  [run]  $version ..."
    psql "$DATABASE_URL" -f "$filepath"
    psql "$DATABASE_URL" -c "INSERT INTO schema_migrations (version) VALUES ('$version');"
    echo "  [done] $version"
  fi
done

echo "=== Migrations complete ==="
