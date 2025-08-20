#!/usr/bin/env bash
# Archive existing alembic version files into alembic/versions/archived
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSIONS_DIR="$ROOT_DIR/alembic/versions"
ARCHIVE_DIR="$VERSIONS_DIR/archived"

mkdir -p "$ARCHIVE_DIR"

shopt -s nullglob
for f in "$VERSIONS_DIR"/*.py; do
  # skip archived directory file if present
  if [[ "$f" == *"/archived/"* ]]; then
    continue
  fi
  echo "Archiving: $(basename "$f")"
  mv "$f" "$ARCHIVE_DIR/"
done

echo "Archived existing alembic versions to $ARCHIVE_DIR"
