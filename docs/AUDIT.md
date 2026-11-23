# HR Portal Audit Report (re-check)

**Date:** 2026-11-23 (final-check fixes)  
**Scope:** Post go-live plan + FINAL-CHECK remediation. Running Docker stack + codebase.  
**Branch:** `main` (local commits ahead of origin).

Statuses: **WORKING** | **PARTIAL** | **BROKEN** | **NOT BUILT** | **NOT TESTED**.

---

## 1. Data inventory (development DB)

| Location | Count / state | Evidence |
| -------- | ------------- | -------- |
| `users` | **2** (`super_admin`, `hr_admin`), both `must_change_password` | `psql` |
| `candidates` / `jobs` | **0** (live kept empty; e2e uses throwaway stack) | `psql` |
| `departments` | **9** reference departments | `psql` |
| `pipeline_stages` / `email_templates` | 6 / 5 | reference data |
| MinIO `cvs` | Empty after cleanup / fixture cleanup | `mc ls` |
| Branding | Org name from settings / `ORG_NAME` | `/api/v1/config` |

---

## 2. Feature check

| Feature | Status | Notes |
| ------- | ------ | ----- |
| Login / logout / forced password change | WORKING | |
| Forgot / reset password (source + **running web**) | WORKING | Web image rebuilt; `/forgot-password` 200; login link present |
| Settings: Users / Org / Departments / Scoring | WORKING | |
| Feature flags (default off) | WORKING | UI 404; API **404 for all methods** (no more 405 on disabled modules) |
| Add candidate (manual + multi-CV) | WORKING | Salary fields; e2e `portal-flows` / `features` |
| Editable profile + document upload / rename / delete | WORKING | Document PATCH/DELETE API + CV viewer |
| CV parse / ATS / match | WORKING | Unusual dates + full names fixed (`rule-1.1`); department goldens |
| Profile tabs + Match Analysis triad | WORKING | Match / ATS / Interview avg side-by-side |
| Notes @mentions, tags, shortlist, email | WORKING | Covered in Playwright portal-flows |
| Bulk toolbar, notification bell | WORKING | |
| Simple interview ratings | WORKING | Always on; shown on table, Kanban, Match Analysis |
| Search + **full filter set** | WORKING | Location, exp, notice, CTC, ATS, rating, status, skills any/all; expanded `q` |
| Cmd+K palette | WORKING | e2e covered |
| Dashboard + CSV export | WORKING | e2e CSV download |
| Kanban drag + Move-to | WORKING | e2e |
| Dark mode + mobile sidebar | WORKING | Touch targets ≥44px on mobile |
| Playwright | WORKING | Default suite excludes screenshots; `make test-e2e-screenshots` separate |
| Backup / restore | WORKING | Always creates empty `cvs/`; restore tolerates missing mirror |
| Public careers / panel interviews / offers / requisitions / audit UI | PARTIAL | Flag-gated; APIs 404 when off |

Automated: **ruff / mypy green**; web **eslint / prettier / tsc** green; pytest expanded (filters + ratings + org 404 matrix); Playwright portal-flows + features specs added.

---

## 3. Security / licenses (spot check)

| Item | Status |
| ---- | ------ |
| No paid APIs / external AI | OK |
| PyMuPDF removed; pypdf + pypdfium2 | OK |
| Valkey instead of Redis 7.4+ | OK |
| ReportLab BSD; MinIO AGPL / ClamAV GPL documented | OK |
| Secure cookies / HSTS / CSP in prod | OK when secured |
| Scores advisory only | OK |

---

## 4. Remaining gaps / follow-ups

1. MinIO public download strategy for prod (`S3_PUBLIC_ENDPOINT_URL`) — `DEPLOY.md`.
2. Confirm production domain, SMTP, and admin email before go-live.
3. Scanned/OCR CVs remain noisier than text PDFs (expected); two-column layouts lower ATS by design.
4. Strengthen **dev** `.env` secrets before any non-local deploy.

---

## 5. Verdict

FINAL-CHECK remediation items 1–9 are implemented and committed. Live DB remains reference-only (no candidate/job rows). Optional modules stay off by default and answer 404 for every HTTP method.
