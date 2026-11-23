# HR Portal Audit Report

**Date:** 2026-11-21  
**Scope:** Read-only inspection of running Docker stack (`hr-portal`) + codebase. No product code changes; only this file and `docs/audit-screenshots/` were created.  
**Note:** Containers were stopped when the audit began; they were started with `docker compose start` (no rebuild). An accidental `make test-e2e` briefly force-recreated `web` (Makefile side effect); web was restored with `NEXT_PUBLIC_API_URL=http://localhost:8001`. Full Playwright e2e via Makefile was **aborted** because it runs `npm ci` and force-recreates web (not read-only).

Statuses used: **WORKING** | **PARTIAL** | **BROKEN** | **NOT BUILT** | **NOT TESTED** (with reason).

Screenshots: `docs/audit-screenshots/` (main pages + selected responsive sizes). Metrics: `docs/audit-screenshots/responsive-metrics.json`.

---

## 1. Dummy data inventory

| Location | What exists | Evidence | How to remove |
|---|---|---|---|
| Postgres `users` | 5 rows (demo staff) | `psql`: `SELECT email,role FROM users` → 5 `@acme.example.com` | Delete extra users or re-seed with only 2; never run `make seed` in prod |
| Postgres `organizations` | 1 (“Acme Corp”) | count=1 | Rename org via admin API/DB; or fresh migrate without seed |
| Postgres `jobs` | 3 (2 open, 1 draft) | count=3; UI Jobs page | Delete/close jobs in UI or `DELETE FROM jobs…` after backups |
| Postgres `candidates` | 43 | count=43 | Truncate candidates + related tables or anonymize |
| Postgres `applications` | 57 | count=57 | Cascade with candidates/jobs cleanup |
| Postgres `documents` / `parsed_profiles` / `match_results` / `ats_checks` | 57 each | counts | Deleted with documents; clear MinIO keys |
| Postgres `pipeline_stages` | 6 | count=6 | Keep (real config); not demo-only |
| Postgres `departments` / `locations` | 2 / 2 | counts | Rename or replace with real org data |
| Postgres `activity_logs` | 59 | count=59 | Optional truncate |
| Postgres `notes` | 1 (audit POST) | was 0, then 1 after API note create | Truncate |
| Postgres `email_logs`, `email_templates`, `notifications`, `interviews`, `offers`, `requisitions`, `scorecards`, `audit_logs`, `consent_records` | 0 | counts | N/A empty |
| Demo accounts (emails only) | `superadmin@acme.example.com`, `hradmin@acme.example.com`, `recruiter@acme.example.com`, `manager@acme.example.com`, `interviewer@acme.example.com` | `psql` + README | Keep 2; delete other 3; rotate passwords |
| Shared demo password | Documented in README / `seed.py` as local-only | README lines ~74–76; `DEMO_PASSWORD` in `apps/api/app/seed.py` | Change all passwords; remove from README for prod deploy notes |
| MinIO bucket `cvs` | **2724** objects (~153 KiB), mostly 45-byte stub PDFs from repeated seeds | `mc ls --recursive --summarize local/cvs` | `mc rm --recursive --force local/cvs` then re-upload real CVs; or wipe volume |
| Seed script | `apps/api/app/seed.py` + `make seed` | file + Makefile | Do not run in production; gate behind `APP_ENV=development` |
| Sample CVs in repo | `apps/api/tests/golden/cvs/*`, `tests/golden/real/*`, `apps/web/e2e/fixtures/cv01_backend.pdf` | glob | Keep for tests; not loaded into prod DB unless seeded |
| Hardcoded UI “Acme” branding | Public layout/careers copy “Acme Careers”, consent “I agree that Acme…” | `apps/web/app/(public)/layout.tsx`, `apply-form.tsx` | Drive from org name / settings |
| README / docs demo credentials | Demo password printed | README | Strip or mark local-only; rotate secrets |

**Seeded candidate emails pattern:** `demoNN@candidates.demo` (plus e2e/`+after00N@example.com` leftovers from prior test runs).

---

## 2. Feature check

| Feature | Status | Evidence |
|---|---|---|
| Login | WORKING | Browser: signed in as `recruiter@acme.example.com` → `/dashboard`. API `POST /api/v1/auth/login` 200 |
| Logout | WORKING | UI user menu → Log out → redirected to `/login`. API logout 204 |
| Password reset (API) | WORKING | `POST /api/v1/auth/forgot-password` → 202; Mailpit message “Reset your HR Portal password” to recruiter |
| Password reset (UI pages) | NOT BUILT | `GET /reset-password` and `/forgot-password` → 404; README says reset page is a later slice |
| Role access | PARTIAL | All 5 roles login OK. Recruiter forbidden on `/users` and `/audit-logs` (403). HR admin can list users. Record-level job scoping in `deps.py` + pytest RBAC collected |
| Create / edit job | WORKING | UI: Create job link, Edit on job detail; pages `/jobs/new`, `/jobs/[id]/edit` exist |
| Publish / close job | WORKING | Job detail shows **Close job**; API has `/jobs/{id}/publish` and `/close` |
| Add candidate with CV (HR) | NOT BUILT (UI) / PARTIAL (API) | API `POST /api/v1/candidates` exists; **no** “Add candidate” control on Candidates page (browser snapshot). Seed shows `manual` source count |
| CV drag-and-drop — apply form | WORKING (single file only) | `CvDropzone` single-file `files?.[0]`; e2e + careers apply path. Multi-file: **NOT BUILT** |
| CV drag-and-drop — HR screen | NOT BUILT | No HR upload dropzone component beyond careers apply |
| CV viewer | WORKING | Profile tab **CV** + `cv-viewer.tsx`; signed download-url API exists |
| CV parsing | WORKING | 57 `parsed_profiles`; Match Analysis shows parsed skills; Celery worker healthy |
| ATS score | WORKING | Analysis API `ats_check.score` (e.g. 100); UI score rings |
| Match score | WORKING | Analysis `match_result.overall_score` (e.g. 92/100); list + Kanban rings |
| Match Analysis tab | WORKING | Browser: Neha Shetty → Match Analysis; advisory disclaimer + strengths/skills |
| Parsed-data correction | PARTIAL | UI Match Analysis has JSON edit + `parsedProfiles.patch`; not fully exercised end-to-end in this audit |
| Candidates search | WORKING | Search box present; filters wire to query params |
| Candidates filters | WORKING | Present in UI: (1) search q, (2) job, (3) stage, (4) source, (5) min score, (6) max score, (7) skill, plus (8) sort control |
| Sorting | WORKING | Sort select: Newest applied / Highest / Lowest score / Name A–Z; column headers Candidate/Score/Applied |
| Pagination | WORKING | Prev/Next on candidates & jobs (“1–3 of 3” on jobs) |
| Kanban drag | PARTIAL | Board renders with `@dnd-kit`; Move menu verified. Actual drag-drop gesture **NOT TESTED** (no drag automation run) |
| Move-to menu | WORKING | Opened “Move Sara Ali” → menuitems Screening/Interview/Offer/Hired/Rejected |
| Reject with reason | WORKING (prior e2e + UI) | Reject dialog component; Rejected column shows reason on profile; e2e spec covers flow. Fresh reject in this session **NOT TESTED** |
| Notes | PARTIAL | API GET/POST notes 200/201; **no notes UI** on profile (Overview/CV/Timeline/Match only) |
| Tags | PARTIAL | API tags on candidate; seed tags e.g. `silver-medalist`; **no tags UI** |
| Shortlist | PARTIAL | API shortlist 200; **no shortlist UI** control observed |
| Bulk actions | PARTIAL | API `bulk-action`; **no bulk toolbar** in UI (`docs/PROGRESS.md` marks partial) |
| Email send | PARTIAL | API `/emails/send`, templates empty; **no compose UI**. Mailpit used for password reset only |
| Notifications | PARTIAL | API returns `[]`; **no notification bell** in top bar |
| Dashboard KPIs | WORKING | Overview cards: open jobs 2, applicants 57, etc. |
| Dashboard charts | PARTIAL | Funnel/sources/trend are **lists**, not charts (`PROGRESS.md`: Recharts not shipped) |
| Ctrl+K / Cmd+K search | NOT BUILT | API `/api/v1/search` 200; no command palette UI; keyboard probe not available after logout. Code has no cmdk component |
| Interviews | NOT BUILT (UI) / PARTIAL (API) | `/interviews` page 404; API POST + `/interviews/mine` 200; e2e skips portal |
| Scorecards | NOT BUILT (UI) / PARTIAL (API) | API scorecard POST; 0 scorecards in DB; no portal page |
| Offers | NOT BUILT (UI) / PARTIAL (API) | `/offers` page 404; API POST-only routes; e2e skips |
| Requisitions | NOT BUILT (UI) / PARTIAL (API) | API GET [] 200; no portal page |
| Settings pages | NOT BUILT | `/settings` 404 |
| Audit log | PARTIAL | API `/audit-logs` (admin); table empty (0). No UI page |
| Data export | WORKING (API) | HR admin `GET …/candidates/{id}/export` 200 with candidate/applications/documents/consents |
| Anonymize | PARTIAL | API route exists (`compliance.py`); **NOT TESTED** live (destructive); no UI |

---

## 3. UI review

### Sidebar & pages

**Portal sidebar (`app-sidebar.tsx`):** Dashboard, Jobs, Candidates only.

**Portal routes present:**

| Page | Notes |
|---|---|
| `/dashboard` | KPIs + list widgets; thin on charts |
| `/jobs`, `/jobs/new`, `/jobs/[id]`, `/jobs/[id]/edit` | Solid |
| `/candidates`, `/candidates/[id]`, `/candidates/compare` | Solid list/profile; compare not opened this audit |
| `/login` | Works |
| `/careers`, `/careers/[slug]`, apply, applied | Public careers works |

**Missing / 404:** `/interviews`, `/offers`, `/settings`, `/forgot-password`, `/reset-password`, notifications UI, admin users UI, audit UI.

### Thin / placeholder

- Dashboard “charts” are plain lists; trend often `1` per day from seed.
- Match Analysis “Component scores: No component breakdown yet” for some seeded profiles.
- Many backend modules have no nav entry (interviews, offers, requisitions, settings, audit, email).

### Unnecessary for two HR users

- Roles: hiring_manager, interviewer (and possibly super_admin) if only admin + recruiter.
- Requisitions / multi-approver offers / interview panel flows.
- Public careers site still useful if they accept external applicants; otherwise optional.

### Inconsistency / clutter

- Purple/indigo + Inter matches design tokens; portal vs “Acme Careers” branding mismatch for a non-Acme org.
- Candidates page filter row is dense (8 controls).
- Phone 390px: fixed 240px sidebar leaves ~150px content (broken usable layout).
- Duplicate-looking names across jobs are seed/application rows (expected) but look noisy.

**Screenshots:** `main-*.png`, `dashboard-1280.png`, selected `resp-*.png` under `docs/audit-screenshots/`.

---

## 4. Responsive check

Method: Chrome CDP `Emulation.setDeviceMetricsOverride` + `Runtime.evaluate` overflow/sidebar/table metrics + screenshots. Full matrix for every page×size was **not** completed (time); candidates covered at all five sizes; careers/login/dashboard sampled at 390.

| Page | 390×844 | 844×390 | 820×1180 | 1280×800 | 1920×1080 |
|---|---|---|---|---|---|
| Login | Shot taken (session redirected to dashboard at 390 during measure: overflowX false). Full login-only matrix **PARTIAL** | NOT TESTED | NOT TESTED | main-login.png (desktop) | NOT TESTED |
| Dashboard | sidebarBroken (aside 240 / main 150); overflowX false; smallTargets 4 | NOT TESTED | NOT TESTED | main-dashboard OK | dashboard-1280 OK |
| Jobs | NOT TESTED at 390 (same sidebar pattern expected) | NOT TESTED | NOT TESTED | main-jobs OK | NOT TESTED |
| Candidates | sidebarBroken; tablesOverflow 1; smallTargets 9; shot | tablesOverflow 1; shot | tablesOverflow 1; shot | OK tablesOverflow 0; shot | OK; shot |
| Kanban | NOT TESTED (expect horizontal board scroll) | NOT TESTED | NOT TESTED | main-kanban OK | NOT TESTED |
| Candidate profile | NOT TESTED | NOT TESTED | NOT TESTED | main-candidate-profile OK | NOT TESTED |
| Match Analysis | NOT TESTED | NOT TESTED | NOT TESTED | main-match-analysis OK | NOT TESTED |
| Careers | overflowX false; smallTargets 4; shot | NOT TESTED | NOT TESTED | main-careers (viewport oddly narrow in one capture) | NOT TESTED |

**Findings:**

- **Phone portrait:** Fixed sidebar consumes majority of width → unusable portal chrome.
- **Tablet / phone landscape:** Candidate **table** overflows parent (`tablesOverflow: 1`) — horizontal scroll inside table region likely.
- **Desktop 1280+:** Candidates table fits; no page-level overflowX.
- **Touch targets:** Multiple controls &lt;44px on candidates (sort headers, pagination, chips) — `smallTargets` ≈ 9.

---

## 5. Users and access

### Roles (`UserRole`)

| Role | Capabilities (from routers / deps) |
|---|---|
| `super_admin` | Admin + org-wide |
| `hr_admin` | Users CRUD/role, audit, export/anonymize, full recruiting |
| `recruiter` | Jobs, applications, candidates, comms, analytics, interviews/offers APIs; **not** `/users` or audit |
| `hiring_manager` | Job-scoped; requisitions; offer approve path |
| `interviewer` | Job-scoped; `/interviews/mine`, scorecards |

### How users are created

- **API:** `POST /api/v1/users` requires `AdminUser` (super_admin / hr_admin).
- **Seed:** `make seed` / `python -m app.seed` creates five demo users.
- **No public signup:** `POST /api/v1/auth/register` → **404**.
- **First admin:** No bootstrap endpoint observed; first admin comes from **seed** or manual DB insert + password hash. Fresh empty DB has no admin until seed or SQL.
- **Forced password change on first login:** **NOT BUILT** — `users` table has no `must_change_password` (columns: email, password_hash, role, lockout, optional `mfa_secret`).

### For only two people (1 admin, 1 recruiter)

1. Create/keep `hr_admin` + `recruiter` with strong unique passwords.  
2. Delete/deactivate `superadmin`, `manager`, `interviewer` (and any extras).  
3. Do **not** run `make seed` on the shared environment.  
4. Wipe demo candidates/MinIO or start from empty volumes + migrate only.  
5. Bind portal to private network / VPN; disable public ports for Postgres/Redis/MinIO/Mailpit.  
6. Optional: hide careers if not needed.

---

## 6. Data storage

| Store | Volume name | Container path | Host Docker path |
|---|---|---|---|
| PostgreSQL | `hr-portal_postgres_data` | `/var/lib/postgresql/data` | `/var/lib/docker/volumes/hr-portal_postgres_data/_data` |
| MinIO | `hr-portal_minio_data` | `/data` | `…/hr-portal_minio_data/_data` |
| Redis | `hr-portal_redis_data` | `/data` | `…/hr-portal_redis_data/_data` |

**`docker compose down -v`:** Deletes all three volumes → **all DB rows, CVs, Redis state lost**. Images remain.

**Backups:** Spec mentions daily backups; **no backup scripts/cron found** in repo. Status: **NOT BUILT**.

### Server deploy changes needed

- Replace default `.env` secrets (JWT, DB, MinIO).  
- Stop publishing Postgres/Redis/MinIO/Mailpit to `0.0.0.0`.  
- Put web+API behind HTTPS reverse proxy; set refresh cookie HTTPS flag (`config.py` comment).  
- Point SMTP at real provider; remove Mailpit.  
- Persistent disk for volumes; backup Postgres + MinIO.  
- `APP_ENV=production`; CORS locked to real origin.  
- Build web with correct `NEXT_PUBLIC_API_URL`.

### Paid / external services

**No paid SaaS wired in runtime code.** Stack is self-hosted.

| Dependency / call | Role | License (typical) |
|---|---|---|
| Docker images: pgvector, redis, Chainguard MinIO, Mailpit, app images | Infra | Various OSS |
| FastAPI, SQLAlchemy, Alembic, Pydantic, Celery, Redis, asyncpg | API | MIT/BSD-like |
| argon2-cffi, PyJWT | Auth | MIT |
| boto3 → MinIO (S3 API) | Object storage | Apache-2.0 |
| pdfplumber, PyMuPDF, python-docx, Pillow, pytesseract | CV extract | OSS (check AGPL for PyMuPDF in commercial use) |
| spaCy + `en_core_web_sm` (local model) | NER | MIT / model CC |
| scikit-learn | Matching helpers | BSD |
| reportlab | Offer PDF | AGPL/commercial dual — **review for prod** |
| Next.js, React, TanStack Query, RHF, Zod, dnd-kit, Radix, Tailwind | Web | MIT |
| Playwright (dev/e2e) | Tests | Apache-2.0 |

**External network calls in app logic:** none required at runtime beyond container DNS (postgres/redis/minio/mailpit). Spec mentions Sentry but **not implemented**. Google Fonts avoided in Docker (`layout.tsx` comment). No OpenAI/Stripe/SendGrid/Auth0 keys in `.env.example`.

---

## 7. Production readiness

| Item | Status | Evidence |
|---|---|---|
| Exposed ports | BROKEN for prod | Compose publishes 3000, 8001, **5432, 6379, 9000, 9001, 1025, 8025** on all interfaces |
| MinIO console | Exposed | `:9001` |
| Mailpit | Exposed | UI `:8025`, SMTP `:1025` |
| Default secrets | BROKEN | `.env` matches `.env.example`: JWT placeholder, `POSTGRES_PASSWORD=change-me`, MinIO `change-me-minio` |
| CORS | PARTIAL | `CORS_ORIGINS` localhost list; OK for local, must tighten |
| HTTPS | NOT BUILT | HTTP only; security headers lack HSTS; cookie HTTPS flag exists in config but unused locally |
| Security headers (API) | WORKING | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `X-XSS-Protection: 0` on `/health` |
| Security headers (Web) | PARTIAL | Next default; no strong CSP observed on `/login` headers |
| Rate limits | PARTIAL | Public apply IP limit (5/hour) + lockout after 5 bad passwords; no general API rate limit |
| File upload validation | WORKING | `cv_validation.py`: magic bytes, 5MB, PDF/DOCX |
| Virus scan | NOT BUILT | Enum `virus_scan_status` seeded CLEAN; no ClamAV integration |
| PII in logs | PARTIAL | Request middleware logs method/path/status only; email bodies/tokens appear in Mailpit (dev). Interview email service embeds names — OK for email, watch logs |
| SMTP real email | PARTIAL | Env SMTP_* ready; currently Mailpit. Password reset works through Mailpit |
| Health checks | WORKING | `/health` ok for api/db/redis; compose healthchecks on services |
| Migrations | WORKING | Alembic head `20261121_0004` |
| Env vars | Documented | `.env.example` complete for local |
| Feature flags | NOT BUILT | No `FEATURE_*` flags to hide modules |

---

## 8. Tests and code health

| Check | Result | Evidence |
|---|---|---|
| API pytest | **52 passed** | `docker exec … pytest -q` → `52 passed in 86.68s` |
| Ruff | **FAIL** — 21 issues | `ruff check app` (PLR0913, etc.) |
| Mypy | **FAIL** — 5 errors / 4 files | seed comparison-overlap; notifications rowcount; reportlab stubs; candidates Decimal |
| Web ESLint | **PASS** | `npm run lint` → no warnings |
| Web `tsc --noEmit` | **PASS** | empty output, exit 0 |
| Playwright e2e | **NOT TESTED** (suite) | `make test-e2e` aborted: force-recreates web + `npm ci` (not audit-safe). Spec file exists with 2 conditional `test.skip` for interviews/offers UI |
| Known skips | e2e interviews/offers UI skipped if pages missing; DB tests skip if Postgres down (`conftest`) |

### TODOs / unfinished (from code + PROGRESS.md)

- Notification bell UI; notes/tags/bulk toolbar UI; Cmd+K palette UI.  
- Interviews / offers / requisitions / settings portal pages.  
- Recharts charts.  
- AUTH-04 TOTP skipped.  
- Retention Celery job partial.  
- `CVParser` abstract `NotImplementedError` in parser base.  
- Virus scan pipeline not implemented.  
- Password reset web pages not shipped.

---

## 9. Summary table

| Feature | Status | Notes |
|---|---|---|
| Login / logout | WORKING | UI + API |
| Password reset | PARTIAL | API + Mailpit OK; no web pages |
| RBAC | WORKING | Enforced; extra roles beyond 2-user need |
| Jobs CRUD / publish / close | WORKING | |
| Careers apply + single CV dropzone | WORKING | Multi-file NOT BUILT |
| HR Add candidate UI | NOT BUILT | API only |
| Candidates list/search/filters/sort/paging | WORKING | 7 filters + sort |
| Kanban + Move-to | WORKING | Drag gesture NOT TESTED |
| Reject with reason | WORKING | |
| Match / ATS / Match Analysis | WORKING | Component bars often empty on seed |
| Parsed correction | PARTIAL | UI present; light test |
| Notes / tags / shortlist / bulk | PARTIAL | API yes, UI no |
| Email / notifications | PARTIAL | API/Mailpit; no portal UI |
| Dashboard KPIs | WORKING | Charts PARTIAL (lists) |
| Ctrl+K search | NOT BUILT | API only |
| Interviews / scorecards / offers / requisitions | NOT BUILT | APIs partial |
| Settings / audit UI | NOT BUILT | Audit API empty |
| Export | WORKING | API |
| Anonymize | PARTIAL | API untested live |
| Demo data | BROKEN for prod | Heavy seed + MinIO stubs |
| Secrets / exposed ports | BROKEN for prod | Defaults + wide publish |
| Automated tests | PARTIAL | pytest green; ruff/mypy fail; e2e not run this audit |
| Mobile responsive portal | BROKEN | Fixed sidebar |
| Backups | NOT BUILT | |
| HTTPS / feature flags | NOT BUILT | |

### Top 10 problems (severity)

1. **Default secrets still in `.env`** (JWT/DB/MinIO) — credential compromise.  
2. **Infrastructure ports exposed** (Postgres, Redis, MinIO console, Mailpit).  
3. **Demo seed + 2700+ stub CVs** unsuitable for real two-person use.  
4. **Demo password documented** and shared across five accounts.  
5. **No first-admin bootstrap / no forced password change** — ops gap.  
6. **Portal unusable on phone** (240px sidebar).  
7. **Core HR workflows missing in UI** (add candidate, notes, tags, email, notifications).  
8. **Interviews/offers/settings/audit UI not shipped** while APIs/partial docs claim progress.  
9. **No backup story** despite SPEC availability target.  
10. **Ruff/mypy failing** — CI quality gate risk; reportlab licensing needs review.

### Recommended cleanup order

1. Rotate all secrets; lock compose ports; disable Mailpit/MinIO console on public binds.  
2. Wipe volumes or truncate demo data; create **two** real users; never re-seed.  
3. Replace Acme branding with real org name.  
4. Ship or drop unfinished modules; add feature flags or remove dead API surface.  
5. Fix mobile nav (drawer/overlay).  
6. Add HR “Add candidate” + notes UI (highest daily value).  
7. Real SMTP + password-reset pages.  
8. Backups (pg_dump + MinIO sync) and restore drill.  
9. HTTPS reverse proxy + HSTS.  
10. Fix ruff/mypy; run e2e in CI without mutating secrets.

### Questions before proceeding

1. Should the **public careers** site stay enabled for external applicants?  
2. Confirm the two users: exact emails/roles (hr_admin + recruiter)?  
3. Wipe **all** demo candidates/CVs, or keep a small sample?  
4. Is **self-hosted only** (no Sentry/email SaaS) a hard requirement?  
5. Target host: single Docker VPS, or k8s? Domain + TLS cert approach?  
6. Do you need interviews/offers in v1 for two HR users, or defer indefinitely?  
7. Accept **PyMuPDF / reportlab** license obligations for production?  
8. May we run a **destructive** reset script (down -v + migrate + create 2 users) in a follow-up?

---

*End of audit.*
