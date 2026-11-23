# Production deployment

> Prefer the newer focused guides: [PRODUCTION-DEPLOYMENT.md](./PRODUCTION-DEPLOYMENT.md), [CLOUDFLARE-TUNNEL-SETUP.md](./CLOUDFLARE-TUNNEL-SETUP.md), [SECURITY-CHECKLIST.md](./SECURITY-CHECKLIST.md), [BACKUP-RESTORE.md](./BACKUP-RESTORE.md), [GO-LIVE-CHECKLIST.md](./GO-LIVE-CHECKLIST.md).

This guide covers a small-footprint go-live using **only free/open-source** components. Two common patterns:

1. **Oracle Cloud Always Free** — a single VM with public IPv4, ports 80/443 open to the internet, Caddy obtains Let's Encrypt certificates.
2. **Home lab / dynamic IP** — **Cloudflare Tunnel** (free) or **DuckDNS** plus port forwarding; Caddy still terminates TLS when the tunnel or DNS points at the VM.

The production stack is `docker-compose.prod.yml`: **Caddy** is the only service published on the host. PostgreSQL, Valkey, MinIO, API, worker, web, and optional ClamAV stay on the internal Compose network.

## Prerequisites

- Linux VM (Ubuntu 22.04+ recommended), Docker Engine and Compose v2 installed.
- A hostname (`DOMAIN`) that resolves to the machine or tunnel endpoint.
- Outbound SMTP (for password resets and notifications).

## 1. Prepare configuration

On the server, in the project directory:

```bash
cp .env.production.example .env
chmod +x scripts/generate-secrets.sh
./scripts/generate-secrets.sh
```

Merge the generated lines from `backups/prod-secrets.env` into `.env` (that file is git-ignored). Then edit `.env` manually:

| Variable | Notes |
| -------- | ----- |
| `DOMAIN`, `ACME_EMAIL` | Public hostname and Let's Encrypt contact |
| `CORS_ORIGINS`, `WEB_BASE_URL` | Must match `https://$DOMAIN` |
| `ORG_NAME` | Shown in the portal and emails |
| `SMTP_*` | Real provider; TLS on port 587 is typical |
| `ENABLE_*` | Keep `false` unless you intentionally enable a module |
| `COOKIE_SECURE=true`, `TRUST_PROXY_HEADERS=true` | Required behind Caddy |
| `S3_PUBLIC_ENDPOINT_URL` | Host browsers use for **presigned CV downloads**. If MinIO is not public, use a dedicated object subdomain or proxy; otherwise leave downloads disabled for external users |

Optional ClamAV:

```bash
# In .env:  CLAMAV_HOST=clamav
docker compose -f docker-compose.prod.yml --profile clamav up -d
```

Optional Celery Beat (only when `RETENTION_REJECTED_DAYS` > 0):

```bash
docker compose -f docker-compose.prod.yml --profile beat up -d
```

## 2. Start the stack

```bash
make prod-up
# or:  docker compose -f docker-compose.prod.yml up -d --build
```

Wait until `docker compose -f docker-compose.prod.yml ps` shows healthy `api`, `web`, and `caddy`.

## 3. Database and first admin

```bash
make prod-migrate
docker compose -f docker-compose.prod.yml exec api python -m app.cli.init_admin
```

Run `init-admin` once for a `super_admin` and once for an `hr_admin`. Generated passwords are shown once unless you use `--password-file`.

Remove demo data before go-live (after a backup):

```bash
make cleanup-demo   # development compose only — in prod use exec on prod file:
docker compose -f docker-compose.prod.yml exec api python -m app.cli.cleanup_demo
```

## 4. Caddy and TLS

`Caddyfile` serves the Next.js app on `/` and proxies `/api/v1/*` and `/health` to the API. HSTS and security headers are set at the edge; the API adds HSTS/CSP when `APP_ENV=production` or `COOKIE_SECURE=true`.

**Oracle Cloud:** open ingress rules for TCP 80 and 443 to the VM.

**Cloudflare Tunnel:** run `cloudflared` on the same host, point the tunnel at `http://localhost:80`, and set `DOMAIN` to your Cloudflare hostname. Let's Encrypt may use TLS-ALPN or DNS depending on setup; with Cloudflare proxying, you may terminate TLS at Cloudflare instead—adjust Caddy only if you use flexible SSL (not recommended).

**DuckDNS:** update DuckDNS to the current public IP, forward ports 80/443 on your router to the VM, set `DOMAIN` to your `*.duckdns.org` name.

## 5. Security checklist

- Refresh tokens use the `HttpOnly`, `Secure` cookie when `COOKIE_SECURE=true` (set in auth router from settings).
- API rate limiting stays enabled via `API_RATE_LIMIT_PER_MINUTE` (default 300); login and apply endpoints have separate limits.
- No database, Redis, or MinIO ports are published in production compose.
- Feature flags (`ENABLE_*`) default off in `.env.production.example`.

## 6. Backups

Nightly backup (database + MinIO mirror, 14-day retention by default):

```bash
make backup-nightly
# Cron example (02:15 UTC daily):
# 15 2 * * * cd /opt/hr-portal && ./scripts/backup.sh >>/var/log/hr-portal-backup.log 2>&1
```

Backups land in `backups/nightly/<YYYYMMDD-HHMMSS>/` with `db.dump` and `cvs/`.

### Restore drill (staging or local — do not practice on live prod without a maintenance window)

Use a **copy** of a nightly backup directory on a non-production machine or stack:

```bash
# Start an isolated prod-style stack with its own .env
docker compose -f docker-compose.prod.yml up -d postgres valkey minio minio-init
docker compose -f docker-compose.prod.yml up -d api worker web

make restore STAMP=20261123-021500
# or:  ./scripts/restore.sh backups/nightly/20261123-021500
```

Verify:

```bash
docker compose -f docker-compose.prod.yml exec api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
docker compose -f docker-compose.prod.yml exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'select count(*) from candidates;'
```

Confirm a CV downloads in the UI after restore if MinIO data was included.

## 7. Retention

`RETENTION_REJECTED_DAYS=0` (default) disables automatic anonymization. When set to a positive number, candidates with only rejected applications older than that window are anonymized, soft-deleted, and CV objects removed from MinIO.

Manual run:

```bash
docker compose -f docker-compose.prod.yml exec api python -m app.cli.retention
```

## 8. Operations

```bash
make prod-logs          # all services
make prod-logs s=api    # one service
make prod-down          # stop (volumes retained)
```

Rebuild after upgrades:

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```