# HR Portal Audit Report (re-check)

**Date:** 2026-11-23  
**Scope:** Post go-live plan (phases 1–6). Running Docker stack + codebase.  
**Commits:** `phase 1` … `phase 6` on `main` (ahead of origin).

Statuses: **WORKING** | **PARTIAL** | **BROKEN** | **NOT BUILT** | **NOT TESTED**.

---

## 1. Data inventory (development DB after cleanup)

| Location | Count / state | Evidence |
| -------- | ------------- | -------- |
| `users` | **2** (`super_admin`, `hr_admin`), both `must_change_password` | `psql` |
| `candidates` / `jobs` | **0** | `psql` |
| `departments` | **9** reference departments | `psql` |
| `pipeline_stages` / `email_templates` | 6 / 5 | reference data |
| MinIO `cvs` | Empty after cleanup | prior cleanup run |
| Demo accounts | Removed; seed gated on `APP_ENV=development` | `make seed-demo` / `cleanup-demo` |
| Branding | Org name from settings / `ORG_NAME` (no Acme) | `/api/v1/config` |

Initial admin credentials live only in git-ignored `backups/credentials/` (never printed in docs).

---

## 2. Feature check

| Feature | Status | Notes |
| ------- | ------ | ----- |
| Login / logout / forced password change | WORKING | `must_change_password`; refresh `pwd` claim |
| Forgot / reset password pages | WORKING | `/forgot-password`, `/reset-password` |
| Settings: Users / Org / Departments / Scoring | WORKING | Admin-gated |
| Feature flags (all default off) | WORKING | UI hidden + API 404; careers site off |
| Add candidate (manual + multi-CV) | WORKING | `/candidates/new`; salary fields; budget badge |
| Editable profile + document upload | WORKING | PATCH candidate; document dropzone |
| CV parse / ATS / match | WORKING | Celery `process_document`; advisory scores only |
| Profile tabs (Overview, CV, Match, Timeline, Notes, Interviews) | WORKING | |
| Notes @mentions, tags, shortlist, email composer | WORKING | |
| Bulk toolbar, notification bell | WORKING | |
| Simple interview ratings | WORKING | Always on (not gated by `ENABLE_INTERVIEWS`) |
| Final score panel + weights | WORKING | Default 50/50; Settings > Scoring |
| Reject + Move-to | WORKING | Kanban + profile header |
| Search (trigram) + filter popover + chips + saved filters | WORKING | |
| Cmd+K palette | WORKING | |
| Dashboard Recharts + date range + CSV | WORKING | Overview respects start/end for applicant counts |
| Days-in-stage amber/red | WORKING | ≥7 amber, ≥14 red |
| Dark mode + mobile sidebar | WORKING | `next-themes` + Sheet |
| Playwright screenshots suite | WORKING (spec) | `e2e/screenshots.spec.ts` → `docs/screenshots/` (run via e2e stack) |
| Public careers | WORKING when flag on | Default **off** |
| Full interview scheduling / offers / requisitions / audit UI | PARTIAL | APIs exist; gated off by flags; UI not primary |
| ClamAV scanning | WORKING when `CLAMAV_HOST` set | Optional prod profile |
| Retention job | WORKING when `RETENTION_REJECTED_DAYS` > 0 | Default **off** |
| Prod compose + Caddy | WORKING (files) | `docker-compose.prod.yml`, `Caddyfile` |
| Nightly backup / restore scripts | WORKING | `scripts/backup.sh`, `restore.sh` |

Automated: **ruff / mypy / pytest 78 passed**; web **tsc + eslint** clean; e2e **8 passed / 3 skipped** (phase 1 accounts + hiring flow).

---

## 3. Security / licenses (spot check)

| Item | Status |
| ---- | ------ |
| No paid APIs / external AI | OK |
| PyMuPDF removed; pypdf + pypdfium2 | OK — golden parity; see `docs/LICENSES.md` |
| Valkey instead of Redis 7.4+ | OK |
| ReportLab BSD (not AGPL) | Documented in `LICENSES.md` |
| Secure cookies / HSTS / CSP in prod | OK when `COOKIE_SECURE` or `APP_ENV=production` |
| Scores never auto-reject / no demographic scoring features | OK |
| Demo passwords stripped from README | OK |

---

## 4. Remaining gaps / follow-ups

1. Capture real PNGs under `docs/screenshots/` (suite exists; needs e2e run with seed).
2. MinIO browser downloads in prod need a public object URL strategy (`S3_PUBLIC_ENDPOINT_URL`) — noted in `DEPLOY.md`.
3. Optional modules (interviews scheduling, offers, requisitions, audit UI) still flag-gated; turn on only when needed.
4. Confirm company display name, Akanksha’s real email, and production domain with the user before go-live.

---

## 5. Verdict

The go-live plan phases **1–6 are implemented and committed**. The portal is an HR-only internal tool with two mandatory admin accounts, optional careers site off by default, advisory scoring only, and a production compose path documented in `docs/DEPLOY.md`.
