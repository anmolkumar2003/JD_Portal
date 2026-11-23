# Go-live checklist

Distinguish **done in repo**, **must run on your Mac Mini**, and **policy / approvals**.

## A. Before first start (manual)

1. [ ] Install / start Docker Desktop on the Mac Mini M2
2. [ ] `cd` to `hr-portal` (workspace root stays `JD_Portal`)
3. [ ] `cp .env.production.example .env` and run `./scripts/generate-secrets.sh`; merge secrets
4. [ ] Set `ORG_NAME`, SMTP, and (if tunneling) prepare to paste the trycloudflare URL into `CORS_ORIGINS` / `WEB_BASE_URL`
5. [ ] Confirm `.env` is not tracked: `git check-ignore -v .env`
6. [ ] Company approval if exposing any real candidate PII beyond localhost

## B. Local production stack (manual)

```bash
cd hr-portal
CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml exec api python -m app.cli.init_admin
docker compose -f docker-compose.prod.yml exec api python -m app.cli.reference_data
curl -sS http://127.0.0.1/health
```

7. [ ] Health OK
8. [ ] Login as super_admin / hr_admin
9. [ ] Create a job, add a candidate + CV, confirm worker parses (not stuck pending)
10. [ ] Export PDF/Excel as admin; confirm recruiter gets 403 on `/api/v1/candidates/{id}/export`
11. [ ] CV preview works (API download path)
12. [ ] `./scripts/backup.sh` creates `MANIFEST.txt`

## C. External Quick Tunnel (optional, temporary)

```bash
cloudflared tunnel --url http://localhost:80
# Update CORS_ORIGINS + WEB_BASE_URL, recreate api/web
```

13. [ ] HTTPS login works
14. [ ] Stop tunnel when finished; do not leave HR data on a public trycloudflare URL

## D. Repo readiness (done / verify)

| Item | Status |
| ---- | ------ |
| Compliance export admin-only | Fixed in code |
| Production secret validation | Fixed in code |
| Secure cookie enforcement | Fixed in code |
| API CV download (MinIO private) | Fixed in code |
| Audit log org scoping | Fixed in code |
| Prod compose: no DB/Valkey/MinIO ports | Verified |
| Worker concurrency=1 for 8 GB | Updated |
| Docs set (this folder) | Updated |
| Git push | **Not done** — needs your approval |
| Full pytest / Playwright on this host | **Blocked** without Docker |

## E. Go-live status definitions

| Status | Meaning |
| ------ | ------- |
| READY FOR LOCAL TESTING | Code + compose + docs ready; you can start Docker and test on localhost |
| READY FOR EXTERNAL TESTING | Local stack verified + Quick Tunnel smoke test OK (non-confidential) |
| READY FOR INTERNAL PILOT | SMTP, backups, encrypted backups, security checklist signed off; no Quick Tunnel for real PII |
| NOT READY | Critical blockers remain |

After this readiness pass (code/docs complete, Docker not running on the agent): **READY FOR LOCAL TESTING**.
