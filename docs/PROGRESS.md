# Build Progress

Legend: `[x]` done · `[~]` partial · `[ ]` pending · `[-]` skipped

## Baseline (Prompts 1–5)

- [x] Scaffold, auth, jobs, careers apply, candidates/Kanban

## Phase 1: CV engine — committed `phase 1: CV engine`

- [x] CV-01..CV-08, CV-10, CAND-10, Celery `process_document`, golden set

## Phase 2: Match Analysis UI — committed `phase 2: Match Analysis UI`

- [x] Match Analysis tab, score filters/sort, compare page
- [x] Notes/tags/shortlist/bulk APIs
- [~] Rich notes composer / bulk toolbar UI (APIs ready)

## Phase 3: Email and notifications — committed `phase 3: email and notifications`

- [x] Models + migration, COMM-01/02 APIs, PIPE-03 hook, notifications APIs
- [~] Notification bell dropdown UI

## Phase 4–7: analytics, interviews, offers, compliance — committed `phase 4-7: ...`

- [x] DASH-01 KPIs + funnel/sources/trend lists; analytics + search APIs
- [~] Recharts charts (list UI for now); Cmd+K palette UI
- [x] INT APIs: schedule, mine, scorecard, summary helpers
- [~] Interviews/My interviews portal pages
- [x] REQ + OFFER APIs incl. local PDF + hired openings decrement
- [~] Requisition/Offer portal pages
- [x] Export/anonymize/audit APIs; security headers; `docs/security-review.md`
- [-] AUTH-04 TOTP (optional — skipped)
- [~] Settings admin UI; retention Celery job

## Phase 8: Quality and demo readiness

- [x] Split docs (`requirements`, `data-model`, `cv-engine`, `api`, `ui`)
- [ ] Seed 30 demo candidates + Playwright e2e + a11y polish
- [ ] Full stack verification

## Blocker

**Docker daemon is not running** (`Cannot connect to the Docker daemon`).  
Need Docker Desktop started to: `make up`, `make migrate`, `make seed`, run DB pytest, and demo the live app.
