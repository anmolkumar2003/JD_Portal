# Hosting reliability (Mac Mini + Docker + Quick Tunnel)

Free, no card, no purchased domain. Local stack on the Mac Mini; temporary public HTTPS via Cloudflare Quick Tunnel.

## What survives what

| Action | Docker containers | Quick Tunnel | Public URL |
| ------ | ----------------- | ------------ | ---------- |
| Close Terminal window | Keeps running (`restart: unless-stopped`) | Keeps running **if** installed as LaunchAgent | Same until tunnel process restarts |
| Put Mac to sleep | Pauses; resumes on wake (may need a moment) | Drops; LaunchAgent restarts it → **new** trycloudflare URL | Changes after wake |
| Shut down / reboot | Comes back after Docker Desktop starts (enable login start) | LaunchAgent restarts tunnel → **new** URL | Changes after reboot |
| Quit Docker Desktop | Stops everything | Tunnel may stay up but origin is down | Site unreachable |

**Quick Tunnel URLs are temporary.** They change whenever `cloudflared` restarts. This is not permanent commercial hosting and is **not** suitable for confidential HR/candidate PII without company security approval.

### Always-on alternatives (not free / need card or domain)

True always-on with a stable hostname usually needs a VPS (often card) or Cloudflare Named Tunnel + a domain. Under the no-card / no-domain constraint, **Mac Mini + Docker + Quick Tunnel** is the best achievable free option, with the sleep/reboot/URL limitations above.

## One-time Mac setup

1. Install Docker Desktop; enable **Start Docker Desktop when you log in**.
2. Install cloudflared: `brew install cloudflared`
3. Ensure prod `.env` uses `CADDYFILE=Caddyfile.tunnel` and only Caddy publishes `80`/`443` (Postgres/Valkey/MinIO stay internal — already true in `docker-compose.prod.yml`).

## Commands

```bash
cd /Users/anmolsmac/JD_Portal/hr-portal

# Stack (independent of Terminal once started)
chmod +x scripts/macos/*.sh
./scripts/macos/stack.sh start
./scripts/macos/stack.sh status
./scripts/macos/stack.sh health
./scripts/macos/stack.sh stop

# Tunnel as LaunchAgent (survives Terminal close; runs at login)
./scripts/macos/tunnel-service.sh install
./scripts/macos/tunnel-service.sh status
./scripts/macos/tunnel-service.sh url
./scripts/macos/tunnel-service.sh stop
./scripts/macos/tunnel-service.sh start
./scripts/macos/tunnel-service.sh uninstall
```

After a new tunnel URL appears:

```bash
# Put the https://….trycloudflare.com value into CORS_ORIGINS and WEB_BASE_URL in .env
CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml up -d api web
```

Logs: `~/Library/Logs/hr-portal/cloudflared.out.log` and `cloudflared.err.log`.

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| No site locally | `./scripts/macos/stack.sh status` then `health`; Docker Desktop running? |
| Tunnel not loaded | `./scripts/macos/tunnel-service.sh status`; re-`install` |
| 502 via tunnel | Caddy/API not healthy; confirm `curl http://127.0.0.1/health` |
| Login cookie fails on public URL | `CORS_ORIGINS` / `WEB_BASE_URL` must match current trycloudflare URL; `COOKIE_SECURE=true` |
| New URL after sleep | Expected — update env and recreate api/web |
