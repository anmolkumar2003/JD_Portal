#!/usr/bin/env bash
# Nightly-style backup: PostgreSQL dump + MinIO bucket mirror under backups/nightly/<stamp>/.
# Optional at-rest encryption: set BACKUP_ENCRYPTION_KEY (32+ char passphrase) to produce
# db.dump.enc and cvs.tar.enc via openssl AES-256-CBC; plaintext copies are removed after success.
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

# Optional: pull encryption key from .env if not already exported (do not echo it).
if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" ]] && grep -q '^BACKUP_ENCRYPTION_KEY=' .env; then
  BACKUP_ENCRYPTION_KEY="$(grep -E '^BACKUP_ENCRYPTION_KEY=' .env | head -1 | cut -d= -f2-)"
  export BACKUP_ENCRYPTION_KEY
fi
if [[ -z "${BACKUP_RETENTION_DAYS:-}" ]] && grep -q '^BACKUP_RETENTION_DAYS=' .env; then
  RETENTION_DAYS="$(grep -E '^BACKUP_RETENTION_DAYS=' .env | head -1 | cut -d= -f2-)"
fi

mkdir -p "$DEST"
# Always create the cvs/ mirror directory, even when the bucket is empty.
# `mc mirror` of an empty source may omit the directory; restore expects it.
mkdir -p "${DEST}/cvs"

echo "Backing up to ${DEST} (compose: ${COMPOSE_FILE})"

docker compose -f "$COMPOSE_FILE" exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' >"${DEST}/db.dump"

if [[ ! -s "${DEST}/db.dump" ]]; then
  echo "ERROR: db.dump is empty — aborting" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" run --rm --no-deps \
  -v "${ROOT}/${DEST}:/backup" \
  minio-init mirror --quiet "local/${S3_BUCKET}" /backup/cvs || true
# Re-ensure empty mirror survives a no-op/failed empty bucket mirror.
mkdir -p "${DEST}/cvs"

# Write a small manifest for restore verification (no PII).
{
  echo "stamp=${STAMP}"
  echo "created_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "db_bytes=$(wc -c <"${DEST}/db.dump" | tr -d ' ')"
  echo "cv_files=$(find "${DEST}/cvs" -type f | wc -l | tr -d ' ')"
} >"${DEST}/MANIFEST.txt"

if [[ -n "${BACKUP_ENCRYPTION_KEY:-}" ]]; then
  if [[ "${#BACKUP_ENCRYPTION_KEY}" -lt 32 ]]; then
    echo "ERROR: BACKUP_ENCRYPTION_KEY must be at least 32 characters" >&2
    exit 1
  fi
  echo "Encrypting backup with AES-256-CBC..."
  openssl enc -aes-256-cbc -pbkdf2 -salt \
    -in "${DEST}/db.dump" -out "${DEST}/db.dump.enc" \
    -pass "env:BACKUP_ENCRYPTION_KEY"
  tar -C "${DEST}" -cf - cvs | openssl enc -aes-256-cbc -pbkdf2 -salt \
    -out "${DEST}/cvs.tar.enc" -pass "env:BACKUP_ENCRYPTION_KEY"
  rm -f "${DEST}/db.dump"
  rm -rf "${DEST}/cvs"
  mkdir -p "${DEST}/cvs"
  echo "encrypted=1" >>"${DEST}/MANIFEST.txt"
fi

echo "Backup complete: ${DEST}"
echo "Verify: cat ${DEST}/MANIFEST.txt"

if [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]] && [[ "${RETENTION_DAYS}" -gt 0 ]]; then
  find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -print0 2>/dev/null \
    | while IFS= read -r -d '' old; do
      echo "Removing backup older than ${RETENTION_DAYS} days: ${old}"
      rm -rf "$old"
    done
fi