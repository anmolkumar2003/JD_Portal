# Build Progress

Track phases and requirement IDs. Update after each phase commit.

Legend: `[x]` done · `[~]` partial · `[ ]` pending · `[-]` skipped

## Baseline (Prompts 1–5) — done before this run

- [x] Scaffold, Docker, Makefile
- [x] AUTH-01, AUTH-02, AUTH-03, AUTH-06
- [x] ORG-01, ORG-02 (partial via seed + lookups)
- [x] JOB-01..JOB-06
- [x] APPLY-01..APPLY-05, APPLY-07
- [x] CAND-01..CAND-04, CAND-09
- [x] PIPE-01, PIPE-02

## Phase 1: CV engine (CV-01..CV-08, Part 8)

- [x] CV-01 Upload/store CV; processing hooked from apply/manual upload
- [x] CV-02 Text extraction + OCR fallback (`extract.py`)
- [x] CV-03 Structured parsing (`parser.py`, `skills.py`, 500+ taxonomy)
- [x] CV-04 ATS-friendliness score A1–A12 (`ats_check.py`)
- [x] CV-05 JD match score (`matcher.py`)
- [x] CV-06 Explanation payload (`explain.py`)
- [x] CV-07 Async parse status + retry (`process_document` Celery task)
- [x] CV-08 Recruiter corrections + re-score (`PATCH /parsed-profiles/{id}`)
- [x] CV-10 Re-score all on job change (`POST /jobs/{id}/rescore`)
- [x] CAND-10 Manual candidate create with CV (`POST /candidates`)
- [x] Celery `process_document`
- [x] Golden set (5 CVs) + precision/recall script
- [x] Endpoints: `GET /applications/{id}/analysis`, `POST /documents/{id}/reprocess`

## Phase 2: Match Analysis UI

- [ ] Part 10 screen 9 Match Analysis tab
- [ ] Score badges (Kanban, table, drawer)
- [ ] Score range + skill filters; sort by score
- [ ] Parsed-data correction UI
- [ ] CAND-07 Compare 2–4 candidates
- [ ] CAND-05 Notes @mentions, tags, shortlist
- [ ] CAND-06 Bulk actions

## Phase 3: Email and notifications

- [ ] COMM-01 Email templates + variables + preview
- [ ] COMM-02 Composer + email logs on timeline
- [ ] COMM-03 In-app notifications (bell)
- [ ] PIPE-03 Stage-triggered auto-emails
- [ ] Mailpit (already in compose)

## Phase 4: Dashboard and analytics

- [ ] DASH-01 KPI cards
- [ ] DASH-02 Charts (Recharts)
- [ ] DASH-03 Time-to-hire / time-in-stage
- [ ] DASH-04 CSV export
- [ ] ADM-04 Global search Ctrl/Cmd+K

## Phase 5: Interviews and scorecards

- [ ] INT-01 Schedule rounds + panel
- [ ] INT-02 ICS invite; reschedule/cancel
- [ ] INT-03 Scorecards from templates
- [ ] INT-04 Hidden feedback until submit
- [ ] INT-06 Aggregated interview summary
- [ ] My interviews page

## Phase 6: Requisitions and offers

- [ ] REQ-01..REQ-03
- [ ] OFFER-01..OFFER-03, OFFER-05
- [ ] Offer letter PDF (local)
- [ ] Hired flow: openings decrement / auto-close

## Phase 7: Admin, compliance, security

- [ ] ADM-01 Audit logs + page
- [ ] ADM-02 Consent, export, anonymize
- [ ] ADM-03 Retention job
- [ ] Settings: users, depts, stages, weights, templates
- [ ] AUTH-04 TOTP (optional)
- [ ] docs/security-review.md

## Phase 8: Quality and demo readiness

- [ ] Seed 30 demo candidates + 5 sample CVs
- [ ] Playwright e2e flows
- [ ] a11y / light-dark / responsive fixes
- [ ] README update
- [ ] Split docs from SPEC.md
