# Production deployment (Mac Mini / small host)

₹0 hosting path for the Internal HR Hiring Portal. Stack: Next.js web, FastAPI API, Celery worker, PostgreSQL 16 + pgvector, Valkey 8, MinIO, Caddy. **Only Caddy publishes host ports** (`80`/`443`) in `docker-compose.prod.yml`.

> **Security note:** Cloudflare Quick Tunnel (`*.trycloudflare.com`) is for **temporary external smoke tests only**. Do not process confidential HR / candidate PII over a Quick Tunnel without company security approval. Prefer a private LAN, VPN, or an approved HTTPS hostname for any real HR data.

Related docs: [LOCAL-DOCKER-SETUP.md](./LOCAL-DOCKER-SETUP.md) · [CLOUDFLARE-TUNNEL-SETUP.md](./CLOUDFLARE-TUNNEL-SETUP.md) · [SECURITY-CHECKLIST.md](./SECURITY-CHECKLIST.md) · [BACKUP-RESTORE.md](./BACKUP-RESTORE.md) · [GO-LIVE-CHECKLIST.md](./GO-LIVE-CHECKLIST.md) · [DEPLOY.md](./DEPLOY.md)

## Hardware target

| Item | Value |
| ---- | ----- |
| Host | Mac Mini M2 (Apple Silicon), 8 GB RAM |
| Compose file | `docker-compose.prod.yml` |
| Worker | Celery `--concurrency=1` (lower RSS on 8 GB) |
| Public ports | `80`, `443` only (DB / Valkey / MinIO stay internal) |

## 1. Prepare `.env`

```bash
cd hr-portal
cp .env.production.example .env
chmod +x scripts/generate-secrets.sh
./scripts/generate-secrets.sh
# Merge backups/prod-secrets.env into .env (JWT_SECRET, Postgres, MinIO keys).
```

Set at minimum:

| Variable | Purpose |
| -------- | ------- |
| `DOMAIN` | Hostname for Caddy (placeholder OK with `Caddyfile.tunnel`) |
| `CORS_ORIGINS` / `WEB_BASE_URL` | Must match the URL browsers use (`https://…`) |
| `APP_ENV=production` | Enables secret validation + Secure cookies |
| `COOKIE_SECURE=true` | Forced on when `APP_ENV=production` |
| `TRUST_PROXY_HEADERS=true` | Behind Caddy / Cloudflare |
| `CV_DOWNLOAD_VIA_API=true` | CVs via API; MinIO not browser-reachable |
| `SMTP_*` | Password reset / notifications |

Production rejects weak `JWT_SECRET` (&lt;32 chars / placeholders) and `localhost` / `*` in `CORS_ORIGINS`.

### Free SMTP options (testing)

| Provider | Notes |
| -------- | ----- |
| Brevo / SendGrid / Mailjet free tier | Create SMTP credentials; port 587 + TLS |
| Gmail App Password | `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USE_TLS=true` |
| Mailpit (local only) | Dev compose only — not for prod |

## 2. Start production stack

```bash
# TLS / Let's Encrypt (public DNS + ports 80/443):
docker compose -f docker-compose.prod.yml up -d --build

# Quick Tunnel (HTTP origin on :80):
CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml up -d --build
```

Wait until `api`, `web`, `worker`, `caddy` are healthy:

```bash
docker compose -f docker-compose.prod.yml ps
```

## 3. Migrations and admins

```bash
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api python -m app.cli.init_admin
# Run once for super_admin and once for hr_admin.
docker compose -f docker-compose.prod.yml exec api python -m app.cli.reference_data
```

## 4. Local URLs

| Mode | URL |
| ---- | --- |
| Prod compose (Caddy) | `http://localhost` (tunnel file) or `https://$DOMAIN` (default Caddyfile) |
| Dev compose | `http://localhost:3000` (web), API `http://localhost:8001` |

## 5. CV processing

Celery worker must be healthy. If a CV stays `pending`/`failed`:

```bash
docker compose -f docker-compose.prod.yml logs worker --tail=100
# Re-queue from the UI (Reprocess) or:
# POST /api/v1/documents/{id}/reprocess  (recruiter+)
```

## 6. What was verified in this readiness pass

| Item | Status |
| ---- | ------ |
| Code inspection + security fixes | Done in repo |
| Unit tests (`test_production_settings`, compliance export) | Added; full pytest needs Docker/Postgres |
| Live Docker start / e2e on this agent host | **Not executed** — Docker daemon was not running |
| Quick Tunnel live URL | **Manual user step** |

See [GO-LIVE-CHECKLIST.md](./GO-LIVE-CHECKLIST.md) for the ordered go-live commands.
