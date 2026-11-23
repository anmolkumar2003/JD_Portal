# Security checklist

Internal HR / Super Admin portal only — not a candidate-facing careers site (keep `ENABLE_PUBLIC_CAREERS=false` unless intentionally enabled).

## Authentication & sessions

- [x] Passwords hashed with Argon2
- [x] Access JWT short TTL (`ACCESS_TOKEN_EXPIRE_MINUTES=15`)
- [x] Refresh token in `HttpOnly` + `SameSite=Lax` cookie; `Secure` forced when `APP_ENV=production`
- [x] Refresh rotation + logout revocation (Redis/Valkey)
- [x] Lockout after failed logins
- [x] Password reset tokens short-lived + bound to password fingerprint
- [ ] Confirm SMTP is TLS in production (`SMTP_USE_TLS=true`) — **manual**
- [ ] Confirm `COOKIE_SECURE=true` behind HTTPS / tunnel HTTPS URL — **manual**

## Authorization

- [x] RBAC via `require_roles` / `AdminUser`
- [x] Job-level access (`scope_jobs_query` / `can_access_job`) for applications, boards, documents
- [x] Candidate notes/timeline require accessible application for non–org-wide roles
- [x] `GET /api/v1/candidates/{id}/export` — **HR_ADMIN / SUPER_ADMIN only** (fixed)
- [x] PDF/Excel exports — admin only + audit
- [x] Audit log listing scoped to actors in the caller's org
- [ ] Spot-check recruiter cannot open manager-only jobs — **run tests / manual**

## Secrets & config

- [x] Production rejects weak `JWT_SECRET` and placeholder MinIO keys
- [x] Production rejects `localhost` / `*` in `CORS_ORIGINS`
- [x] `.env` / `backups/` gitignored; `scripts/generate-secrets.sh` writes mode `600`
- [ ] Merge generated secrets into server `.env` — **manual**
- [ ] Never commit `.env`, dumps, or CV binaries — **verify before push**

## Data & storage

- [x] PostgreSQL / Valkey / MinIO **not** published in `docker-compose.prod.yml`
- [x] CV downloads default via API (`CV_DOWNLOAD_VIA_API=true`) — MinIO private
- [x] Download tokens short-lived (5 minutes)
- [x] Upload MIME/magic validation + size limit
- [ ] Optional ClamAV profile if policy requires — **manual**
- [ ] Encrypted backups (`BACKUP_ENCRYPTION_KEY`) for off-box copies — **recommended**

## Network & headers

- [x] Caddy security headers (HSTS on TLS Caddyfile)
- [x] API `SecurityHeadersMiddleware` (HSTS/CSP when hardened)
- [x] Rate limits (API + login + forgot-password)
- [x] `TRUST_PROXY_HEADERS=true` only behind your proxy
- [ ] Quick Tunnel: treat as temporary; no confidential HR data without approval — **policy**

## Audit & PII

- [x] Audit actions for export / anonymize / auth events
- [x] Export/audit payloads avoid dumping notes/emails into diffs where designed
- [ ] Retention policy (`RETENTION_REJECTED_DAYS`) agreed with legal — **manual**

## Roles (summary)

| Role | Typical access |
| ---- | -------------- |
| `super_admin` | Full org + user admin + compliance export |
| `hr_admin` | Same operational admin as above for HR |
| `recruiter` | Jobs/candidates org-wide; not user admin / compliance export |
| `hiring_manager` | Assigned jobs only |
| `interviewer` | Panel jobs only |
