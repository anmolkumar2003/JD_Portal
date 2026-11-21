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

- [ ] CV-01 Upload/store CV; inline viewer (viewer exists; processing wired)
- [ ] CV-02 Text extraction + OCR fallback
- [ ] CV-03 Structured parsing
- [ ] CV-04 ATS-friendliness score A1–A12
- [ ] CV-05 JD match score
- [ ] CV-06 Explanation payload
- [ ] CV-07 Async parse status + retry
- [ ] CV-08 Recruiter corrections + re-score
- [ ] CV-10 Re-score all on job change (endpoint)
- [ ] CAND-10 Manual candidate create with CV
- [ ] Celery `process_document`
- [ ] Golden set + precision/recall script

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
