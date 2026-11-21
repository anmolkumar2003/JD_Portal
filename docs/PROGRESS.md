# Build Progress

Legend: `[x]` done · `[~]` partial · `[ ]` pending · `[-]` skipped

## Baseline (Prompts 1–5)

- [x] Scaffold, Docker, Makefile
- [x] AUTH-01, AUTH-02, AUTH-03, AUTH-06
- [x] ORG-01, ORG-02
- [x] JOB-01..JOB-06
- [x] APPLY-01..APPLY-05, APPLY-07
- [x] CAND-01..CAND-04, CAND-09
- [x] PIPE-01, PIPE-02

## Phase 1: CV engine

- [x] CV-01..CV-08, CV-10, CAND-10
- [x] Celery `process_document`, analysis endpoints, golden set

## Phase 2: Match Analysis UI

- [x] Match Analysis tab (score ring, components, skills, ATS, corrections)
- [x] Score filters + sort by score
- [x] Compare page (CAND-07)
- [x] Notes/tags/shortlist/bulk APIs (CAND-05/06) — UI wiring partial
- [~] Full notes UI + bulk UI on table (backend ready)

## Phase 3: Email and notifications

- [x] Models + migration for email_templates, email_logs, notifications, notes
- [x] COMM-01/02 APIs (templates, preview, send, logs)
- [x] PIPE-03 stage-triggered email hook
- [x] COMM-03 notifications APIs
- [~] Bell dropdown UI
- [x] Mailpit in compose

## Phase 4: Dashboard and analytics

- [x] DASH-01 KPI cards on dashboard
- [~] DASH-02 charts (table/list fallback; Recharts not installed yet)
- [~] DASH-03/04 time-to-hire + CSV export API present
- [x] ADM-04 search API (`GET /search`)
- [~] Ctrl/Cmd+K palette UI

## Phase 5: Interviews and scorecards

- [x] Models + migration
- [ ] INT-01..04, INT-06 routers/UI

## Phase 6: Requisitions and offers

- [x] Models + migration
- [ ] REQ/OFFER routers/UI + PDF letter

## Phase 7: Admin, compliance, security

- [x] Models: audit_logs, consent_records
- [x] docs/security-review.md
- [ ] Settings UI, audit middleware page, anonymize/export/retention
- [-] AUTH-04 TOTP (optional — skipped for later)

## Phase 8: Quality and demo readiness

- [x] Split docs from SPEC.md
- [ ] Seed 30 candidates
- [ ] Playwright e2e
- [ ] a11y / README polish
- [ ] Full stack verification (blocked: Docker daemon not running)

## Blockers

1. **Docker Desktop / daemon is not running** on this machine — cannot `docker compose up`, migrate, or run DB-backed pytest / live demo until it is started.
