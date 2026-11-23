#!/usr/bin/env bash
# Restore PostgreSQL and MinIO from a stamp directory under backups/nightly/ (or BACKUP_ROOT).
# Usage:  ./scripts/restore.sh 20261123-020000
#         ./scripts/restore.sh backups/nightly/20261123-020000
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_ROOT="${BACKUP_ROOT:-backups/nightly}"
S3_BUCKET="${S3_BUCKET:-cvs}"
STAMP="${1:-}"

if [[ -z "$STAMP" ]]; then
  echo "Usage: $0 <stamp-or-path>" >&2
  echo "Example: $0 20261123-020000" >&2
  exit 1
fi

if [[ -d "$STAMP" ]]; then
  DEST="$STAMP"
elif [[ -d "${BACKUP_ROOT}/${STAMP}" ]]; then
  DEST="${BACKUP_ROOT}/${STAMP}"
else
  echo "Backup not found: ${STAMP}" >&2
  exit 1
fi

if [[ ! -f "${DEST}/db.dump" ]]; then
  echo "Missing ${DEST}/db.dump" >&2
  exit 1
fi

# Tolerate backups taken when the MinIO bucket was empty (no cvs/ directory).
if [[ ! -d "${DEST}/cvs" ]]; then
  echo "Note: ${DEST}/cvs missing — treating as empty MinIO mirror"
  mkdir -p "${DEST}/cvs"
fi

if [[ ! -f .env ]]; then
  echo "Missing .env in ${ROOT}" >&2
  exit 1
fi

echo "WARNING: This replaces the live database and overwrites bucket ${S3_BUCKET}."
echo "Source: ${DEST}"
read -r -p "Type RESTORE to continue: " confirm
if [[ "$confirm" != "RESTORE" ]]; then
  echo "Aborted."
  exit 1
fi

echo "Stopping workers to avoid writes during restore..."
docker compose -f "$COMPOSE_FILE" stop worker beat 2>/dev/null || true

echo "Restoring PostgreSQL..."
docker compose -f "$COMPOSE_FILE" exec -T postgres sh -c \
  'dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
cat "${DEST}/db.dump" | docker compose -f "$COMPOSE_FILE" exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl'

echo "Restoring MinIO bucket..."
docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
  -v "${ROOT}/${DEST}/cvs:/backup/cvs:ro" \
  minio-init mirror --overwrite --quiet /backup/cvs "local/${S3_BUCKET}"

docker compose -f "$COMPOSE_FILE" start worker 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" --profile beat start beat 2>/dev/null || true

echo "Restore finished from ${DEST}"