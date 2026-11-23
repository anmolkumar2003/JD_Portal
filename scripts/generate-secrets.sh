#!/usr/bin/env bash
# Generate strong random values into a git-ignored file. Safe to run on the server before go-live.
# Does not print secrets to the terminal.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/backups/prod-secrets.env"

mkdir -p "$(dirname "$OUT")"
umask 077

POSTGRES_PASSWORD="$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"
MINIO_USER="hrminio$(openssl rand -hex 4)"
MINIO_PASSWORD="$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"
JWT_SECRET="$(openssl rand -base64 64 | tr -d '\n')"

{
  echo "# Generated $(date -u +%Y-%m-%dT%H:%M:%SZ) — merge into .env; do not commit."
  echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
  echo "MINIO_ROOT_USER=${MINIO_USER}"
  echo "MINIO_ROOT_PASSWORD=${MINIO_PASSWORD}"
  echo "S3_ACCESS_KEY_ID=${MINIO_USER}"
  echo "S3_SECRET_ACCESS_KEY=${MINIO_PASSWORD}"
  echo "JWT_SECRET=${JWT_SECRET}"
} >"$OUT"

chmod 600 "$OUT"
echo "Wrote secret placeholders to backups/prod-secrets.env (mode 600)."
echo "Review .env.production.example, copy to .env, then append or merge this file."