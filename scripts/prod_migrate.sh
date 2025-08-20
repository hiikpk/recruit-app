#!/usr/bin/env bash
set -euo pipefail

# Usage: run this on the host that has network access to the production Postgres and the repo checked out.
# It expects: $DATABASE_URL set (Postgres connection URL), a working python virtualenv with alembic available,
# and permission to run pg_dump/pg_restore. This script will:
#  - create a pg_dump backup
#  - render alembic SQL to a file for review
#  - run alembic upgrade head
#  - show alembic current --verbose

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR="/tmp/prod_db_backups"
mkdir -p "$BACKUP_DIR"

if [ -z "${DATABASE_URL-}" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set"
  echo "Set DATABASE_URL=postgresql://user:pass@host:port/dbname and run again"
  exit 2
fi

BACKUP_FILE="$BACKUP_DIR/recruiting-db-$TIMESTAMP.dump"

echo "[1/6] Backing up production database to: $BACKUP_FILE"
echo "Running: pg_dump --format=custom --file=$BACKUP_FILE \"$DATABASE_URL\""
pg_dump --format=custom --file="$BACKUP_FILE" "$DATABASE_URL"
echo "Backup complete"

echo "\n[2/6] Generating alembic SQL for review (alembic upgrade --sql head)"
SQL_FILE="/tmp/alembic_upgrade_head_$TIMESTAMP.sql"
alembic upgrade --sql head > "$SQL_FILE"
echo "Wrote SQL preview to: $SQL_FILE"
echo "Please review the SQL for any destructive statements before proceeding."

read -p "Proceed to apply migrations to production now? (y/N): " yn
case "$yn" in
  [Yy]* ) echo "Proceeding..." ;;
  * ) echo "Aborting per user request. Backup remains at $BACKUP_FILE" ; exit 0 ;;
esac

echo "\n[3/6] Stopping web/worker processes (manual step)"
echo "IMPORTANT: Stop web/worker processes to avoid concurrent schema changes."
echo "If your platform provides a maintenance mode or one-click stop, enable it now."
read -p "Have you stopped web/worker processes? (y/N): " stopped
case "$stopped" in
  [Yy]* ) echo "Continuing..." ;;
  * ) echo "Please stop processes and re-run the script." ; exit 1 ;;
esac

echo "\n[4/6] Applying alembic upgrade head"
alembic upgrade head
echo "alembic upgrade head finished"

echo "\n[5/6] Checking alembic current --verbose"
alembic current --verbose || true

echo "\n[6/6] Quick smoke checks"
echo " - Run health endpoint (if available)"
echo "   curl -I --max-time 5 <APP_HEALTH_ENDPOINT>"
echo " - List interviews table columns via psql:"
echo "   psql \"$DATABASE_URL\" -c \"\d+ interviews\""

echo "Migration script finished. If something failed, you can restore the DB from $BACKUP_FILE:\n"
echo "  pg_restore --clean --if-exists --dbname=\"$DATABASE_URL\" $BACKUP_FILE"
