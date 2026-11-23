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

if [[ ! -f .env ]]; then
  echo "Missing .env in ${ROOT}" >&2
  exit 1
fi

if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]] && grep -q '^BACKUP_ENCRYPTION_KEY=' .env; then
  BACKUP_ENCRYPTION_KEY="$(grep -E '^BACKUP_ENCRYPTION_KEY=' .env | head -1 | cut -d= -f2-)"
  export BACKUP_ENCRYPTION_KEY
fi

WORK="${DEST}"
CLEANUP_WORK=0
if [[ -f "${DEST}/db.dump.enc" ]]; then
  if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
    echo "Encrypted backup requires BACKUP_ENCRYPTION_KEY in the environment or .env" >&2
    exit 1
  fi
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/hr-portal-restore.XXXXXX")"
  CLEANUP_WORK=1
  trap '[[ "$CLEANUP_WORK" -eq 1 ]] && rm -rf "$WORK"' EXIT
  echo "Decrypting backup into temporary directory..."
  openssl enc -d -aes-256-cbc -pbkdf2 \
    -in "${DEST}/db.dump.enc" -out "${WORK}/db.dump" \
    -pass "env:BACKUP_ENCRYPTION_KEY"
  mkdir -p "${WORK}/cvs"
  if [[ -f "${DEST}/cvs.tar.enc" ]]; then
    openssl enc -d -aes-256-cbc -pbkdf2 \
      -in "${DEST}/cvs.tar.enc" -pass "env:BACKUP_ENCRYPTION_KEY" \
      | tar -C "${WORK}" -xf -
  fi
elif [[ -f "${DEST}/db.dump" ]]; then
  WORK="${DEST}"
else
  echo "Missing ${DEST}/db.dump or ${DEST}/db.dump.enc" >&2
  exit 1
fi

# Tolerate backups taken when the MinIO bucket was empty (no cvs/ directory).
if [[ ! -d "${WORK}/cvs" ]]; then
  echo "Note: ${WORK}/cvs missing — treating as empty MinIO mirror"
  mkdir -p "${WORK}/cvs"
fi

echo "WARNING: This replaces the live database and overwrites bucket ${S3_BUCKET}."
echo "Source: ${DEST}"
if [[ -f "${DEST}/MANIFEST.txt" ]]; then
  echo "--- MANIFEST ---"
  cat "${DEST}/MANIFEST.txt"
  echo "----------------"
fi
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
cat "${WORK}/db.dump" | docker compose -f "$COMPOSE_FILE" exec -T postgres sh -c \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl'

echo "Restoring MinIO bucket..."
docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
  -v "${WORK}/cvs:/backup/cvs:ro" \
  minio-init mirror --overwrite --quiet /backup/cvs "local/${S3_BUCKET}"

docker compose -f "$COMPOSE_FILE" start worker 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" --profile beat start beat 2>/dev/null || true

echo "Restore finished from ${DEST}"
echo "Verify health: docker compose -f ${COMPOSE_FILE} exec api python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')\""