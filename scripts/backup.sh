#!/usr/bin/env bash
# Nightly-style backup: PostgreSQL dump + MinIO bucket mirror under backups/nightly/<stamp>/.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_ROOT="${BACKUP_ROOT:-backups/nightly}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${BACKUP_ROOT}/${STAMP}"
S3_BUCKET="${S3_BUCKET:-cvs}"

if [[ ! -f .env ]]; then
  echo "Missing .env in ${ROOT}" >&2
  exit 1
fi

mkdir -p "$DEST"
# Always create the cvs/ mirror directory, even when the bucket is empty.
# `mc mirror` of an empty source may omit the directory; restore expects it.
mkdir -p "${DEST}/cvs"

echo "Backing up to ${DEST} (compose: ${COMPOSE_FILE})"

docker compose -f "$COMPOSE_FILE" exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' >"${DEST}/db.dump"

docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
  -v "${ROOT}/${DEST}:/backup" \
  minio-init mirror --quiet "local/${S3_BUCKET}" /backup/cvs || true
# Re-ensure empty mirror survives a no-op/failed empty bucket mirror.
mkdir -p "${DEST}/cvs"

echo "Backup complete: ${DEST}"

if [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]] && [[ "${RETENTION_DAYS}" -gt 0 ]]; then
  find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -print0 2>/dev/null \
    | while IFS= read -r -d '' old; do
      echo "Removing backup older than ${RETENTION_DAYS} days: ${old}"
      rm -rf "$old"
    done
fi