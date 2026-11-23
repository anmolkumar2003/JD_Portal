# Cloudflare Quick Tunnel setup (temporary testing)

Expose the local production stack at a random `https://*.trycloudflare.com` URL **without** buying a domain or opening router ports.

> For Terminal-independent tunnel + Docker restart behavior, see [HOSTING-RELIABILITY.md](./HOSTING-RELIABILITY.md).

## Limitations (read first)

| Topic | Detail |
| ----- | ------ |
| Cost | Free Quick Tunnel — no Cloudflare account required for `trycloudflare.com` |
| Stability | URL **changes every time** you restart `cloudflared` |
| Security | Traffic is encrypted to Cloudflare, but the hostname is guessable/public while live. **Not suitable for confidential HR / candidate PII** without company security approval |
| Cookies | Use the `https://…trycloudflare.com` origin in `CORS_ORIGINS` / `WEB_BASE_URL`. Refresh cookie needs `Secure` (forced in production) — HTTPS tunnel URL satisfies that |
| CVs | Keep `CV_DOWNLOAD_VIA_API=true` so downloads stay on the same origin (MinIO stays private) |
| Background jobs | Celery worker runs inside Compose; tunnel only fronts Caddy. Jobs do not need the tunnel |
| Uploads | Multipart uploads go through Caddy → API; Quick Tunnel can be slower on large CVs |

## Origin protocol / port (from this repo)

`docker-compose.prod.yml` publishes Caddy as:

- `80:80` (HTTP)
- `443:443` (HTTPS / ACME — unused for Quick Tunnel)

Quick Tunnel must point at **HTTP `localhost:80`** and use **`Caddyfile.tunnel`** (plain `:80`, no Let's Encrypt).

## Steps

### 1. Install cloudflared (Mac)

```bash
brew install cloudflared
# or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

### 2. Configure env for the tunnel URL

Start the stack first with a placeholder, then update CORS after you see the URL — or restart API after setting:

```bash
cd hr-portal
cp .env.production.example .env
./scripts/generate-secrets.sh
# Merge backups/prod-secrets.env into .env

# Temporary values until cloudflared prints the URL:
# DOMAIN=portal.local
# CADDYFILE=Caddyfile.tunnel
# APP_ENV=production
# COOKIE_SECURE=true
# TRUST_PROXY_HEADERS=true
# CV_DOWNLOAD_VIA_API=true
# CORS_ORIGINS=https://PLACEHOLDER.trycloudflare.com
# WEB_BASE_URL=https://PLACEHOLDER.trycloudflare.com
```

### 3. Start the stack (HTTP Caddy)

```bash
cd hr-portal
CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api python -m app.cli.init_admin
```

Confirm local origin:

```bash
curl -sS http://127.0.0.1/health
# expect JSON ok / healthy
```

### 4. Exact tunnel command

```bash
cloudflared tunnel --url http://localhost:80
```

cloudflared prints a line like:

```text
https://random-words-xxxx.trycloudflare.com
```

### 5. Point the app at that URL

Edit `.env`:

```bash
CORS_ORIGINS=https://random-words-xxxx.trycloudflare.com
WEB_BASE_URL=https://random-words-xxxx.trycloudflare.com
```

Reload API/web so settings refresh:

```bash
CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml up -d api web
```

Open the printed HTTPS URL → `/login`.

### 6. Stop

```bash
# Ctrl+C cloudflared
CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml down
# Volumes retained — data is kept
```

## Do not expose

- Postgres `5432`
- Valkey `6379`
- MinIO `9000` / `9001`

None of these are published in `docker-compose.prod.yml`. Do not add host port mappings for “convenience.”

## Status of this doc vs live test

| Item | Status |
| ---- | ------ |
| Compose / Caddyfile.tunnel / env template | Prepared in repo |
| Live `cloudflared` run on agent host | **Not executed** (Docker daemon unavailable) |
| User must run tunnel command locally | **Required** |
