# Backup and restore

Covers PostgreSQL (`pg_dump -Fc`) and MinIO CV bucket mirror. **Never** delete Docker volumes as a “cleanup” step during restore drills on live data.

## Nightly / production backup

```bash
cd hr-portal
# Uses docker-compose.prod.yml by default
./scripts/backup.sh
# or: make backup-nightly
```

Output: `backups/nightly/<YYYYMMDD-HHMMSS>/`

| File | Meaning |
| ---- | ------- |
| `db.dump` | PostgreSQL custom-format dump |
| `cvs/` | MinIO bucket mirror (may be empty) |
| `MANIFEST.txt` | Stamp, sizes, file count (no PII) |
| `db.dump.enc` / `cvs.tar.enc` | Present when `BACKUP_ENCRYPTION_KEY` is set (plaintext removed) |

### Encryption (recommended for copies leaving the Mac Mini)

```bash
# In .env (32+ characters). Never commit this value.
BACKUP_ENCRYPTION_KEY="$(openssl rand -base64 48)"
./scripts/backup.sh
```

Uses `openssl enc -aes-256-cbc -pbkdf2`.

### Dev / manual backup

```bash
make backup   # → backups/manual/<stamp>/
```

### Cron example

```cron
15 2 * * * cd /path/to/hr-portal && ./scripts/backup.sh >>/var/log/hr-portal-backup.log 2>&1
```

Retention: `BACKUP_RETENTION_DAYS` (default 14) deletes older stamp directories under `backups/nightly/`.

## Restore

**Destructive to the live DB and CV bucket.** Type `RESTORE` when prompted. Prefer a maintenance window and a prior fresh backup.

```bash
./scripts/restore.sh 20261123-021500
# or: make restore STAMP=20261123-021500
# Encrypted stamps need BACKUP_ENCRYPTION_KEY in env/.env
```

The script:

1. Stops `worker` / `beat`
2. Recreates the database and `pg_restore`s
3. Mirrors `cvs/` back into MinIO
4. Restarts workers

### Verify after restore

```bash
docker compose -f docker-compose.prod.yml exec api \
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
docker compose -f docker-compose.prod.yml exec postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select count(*) from candidates;"'
# Log in → open a candidate → confirm CV preview/download
```

## What was tested

| Action | Status |
| ------ | ------ |
| Scripts updated (manifest + optional encryption) | Done in repo |
| Live backup/restore on this agent host | **Not executed** (Docker daemon unavailable) |
| Prior repo backups under `backups/manual/` | Exist from earlier work; do not commit |

## Safety rules

- Do **not** run `docker compose down -v` unless you intentionally destroy data.
- Do **not** practice restore on production without a backup of the current state.
- Keep `backups/` gitignored.
