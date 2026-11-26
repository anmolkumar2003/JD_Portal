# Build Progress

Legend: `[x]` done · `[~]` partial · `[ ]` pending · `[-]` skipped

## Earlier build (before the go-live plan)

- [x] Scaffold, auth, jobs, careers apply, candidates and Kanban
- [x] CV engine: parsing, ATS check, JD match, Celery `process_document`, golden set
- [x] Match Analysis tab, score filters and sort, compare page
- [x] APIs for notes, tags, shortlist, bulk actions, email templates, notifications, analytics,
      interviews, requisitions, offers, export, anonymize and audit
- [-] AUTH-04 TOTP (optional, skipped)

## Go-live plan

### Phase 1: cleanup, users, security

- [x] Pre-cleanup backup: database dump and MinIO listing in `backups/pre-cleanup/` (git-ignored)
- [x] Demo data removed from the development database; demo passwords removed from code and docs
- [x] `make init-admin` (interactive; role prompt; strong password or a generated one); the
      super_admin and the hr_admin (Akanksha) accounts created
- [x] `make seed-demo` gated on `APP_ENV=development`; password from `DEMO_PASSWORD` or generated;
      tests mock storage so no stub files reach MinIO
- [x] Forced password change at first sign-in (`must_change_password`); a password change or
      reset signs out other sessions
- [x] Settings > Users: create (temporary password), change role, deactivate, reset password;
      assignable roles hr_admin, super_admin, recruiter; last-admin and self-demotion guards
- [x] `/forgot-password` and `/reset-password` pages
- [x] "Acme" replaced by `ORG_NAME` and Settings > Organization (name, logo); `{{org_name}}` in
      emails
- [x] The 9 reference departments; Settings > Departments; department filter on the applications
      API (the dropdowns in Add Candidate and the candidate filters come in Phases 2 and 4)
- [x] Skill taxonomy: department skills and synonyms filled in; no synonym maps to two skills
- [x] Feature flags `ENABLE_PUBLIC_CAREERS`, `ENABLE_INTERVIEWS`, `ENABLE_OFFERS`,
      `ENABLE_REQUISITIONS`, `ENABLE_AUDIT_UI`, all off by default: hidden in the UI, 404 from
      the API; audit logging stays on
- [x] PyMuPDF (AGPL) replaced by pypdf and pypdfium2 with identical golden results; Redis
      replaced by Valkey; licenses in `docs/LICENSES.md`
- [x] Ruff and mypy clean; Alembic drift fixed (`20261123_0006`), `alembic check` clean
- [x] `make test-e2e` runs in an isolated throwaway stack; it does not touch the development
      containers or `.env`

### Phase 2: Add Candidate — committed `phase 2: add candidate`

- [x] Manual form with salary fields (current/expected/offered × amount, currency, pa/pm,
      negotiable), multi-CV drop zone, localStorage draft autosave, CV autofill with
      "from CV" badges, duplicate email/phone warning, budget badge, editable profile and
      document upload; APIs: parse-cv, duplicates, expanded create/patch

### Phase 3: review, notes, interview rating — committed `phase 3: review, notes, interview rating`

- [x] Profile tabs (Notes, Interviews), parsed-data correction form, notes with @mentions,
      email composer, bulk toolbar, notification bell, simple interview ratings (always on),
      final-score panel + Settings scoring weights (default 50/50), Move-to + reject on profile

### Phase 4: search and filters — committed `phase 4: search and filters`

- [x] Trigram + ILIKE search, filter popover with chips/Clear all/URL state (incl. tag,
      shortlisted, department, dates), named saved filter sets, jobs filter chips, Cmd+K palette

### Phase 5: dashboard, polish, responsive — committed `phase 5: dashboard, polish, responsive`

- [x] Recharts dashboard (KPIs, date range, CSV export), days-in-stage badges (amber 7 / red 14),
      design tokens, skeletons, toasts, dark mode toggle, mobile sidebar sheet, Playwright
      screenshot suite → `docs/screenshots/`

### Phase 6: go-live package — committed `phase 6: go-live package`

- [x] Production compose with Caddy, secrets script, SMTP, hardening (HSTS/CSP/secure cookies),
      nightly backups + restore, ClamAV, retention job (default off), `DEPLOY.md`, `USER-GUIDE.md`

### Phase 7: candidate PDF summary and Excel export

- [x] PDF summary (ReportLab, BSD-3-Clause): profile + bulk ZIP; options dialog for salary /
      contact / HR notes; org branding; advisory scores; HR-only; audited; not stored
- [x] Excel export (openpyxl, MIT): current filters or selection, max 5,000 rows, formula
      injection guard, meta sheet; HR-only; audited; not stored
- [x] pytest + Playwright coverage; `USER-GUIDE.md` and `LICENSES.md` updated

### FINAL

- [x] Re-audit written to `docs/AUDIT.md` (2026-11-23)

### Feature: permanent delete and required fields (`feature/delete-and-required-fields`)

- [x] A1–A7: Admin-only permanent delete (profile + bulk), typed confirmation, hard delete with
      MinIO orphan cleanup and CV-task cancel, audit without PII, Anonymize kept as softer
      action, toast/redirect/cache refresh, pytest + Playwright
- [x] B1–B7: Draft MinIO area (24h expiry + cleanup), preview parse without creating candidates,
      required first/last/email/phone/job on client and API, duplicate warnings, draft→permanent
      save and cancel cleanup, multi-CV review table with partial save, pytest + Playwright
- [x] `docs/USER-GUIDE.md` updated for delete and draft add-candidate flows

### Follow-up: delete visibility and HR-only accounts (`fix/delete-visibility-hr-admin-only`)

- [x] Root cause of "no delete option": the running web images predated the feature and could not
      be rebuilt because the Dockerfile copies `apps/web/.npmrc`, which was never committed.
      File added; prod `api`, `worker`, `web` rebuilt and migrations `0011`/`0012` applied.
- [x] Candidate menu now reads **Actions** (was an icon only); Delete/Anonymize unchanged.
- [x] `beat` now starts by default (dev and prod) with a writable schedule file, so the hourly
      orphan-file and expired-draft cleanups actually run.
- [x] Users dialog offers only HR Admin and Super Admin (API enum unchanged).
- [x] `make remove-user EMAIL=…` (audited, last-admin guard); "UI Review" account removed.

### Feature: Quick fill (`feature/quick-fill`)

HR Admin / Super Admin paste a sentence or a few lines into **Add candidate** or the profile
**Edit** dialog and review the extracted values before anything touches the form. Free,
open-source tools only; no external AI API, no paid service.

- [x] 1. UI: collapsible glass **Quick fill** card, placeholder example, **Extract**, optional
      on-page history (kept in component state only, never stored)
- [x] 2. `POST /candidates/quick-parse`: login + `hr_admin`/`super_admin`, 30 requests per minute
      per user, 2,000 character limit (422 `text_too_long`, text never echoed back); returns the
      fields without saving or storing the text; the text is never logged
- [x] 3. Pure Python engine in `app/cv_engine/quick_fill/` (no FastAPI imports): regex, spaCy NER
      (`en_core_web_sm`), rule dictionaries in `data/*.json`, the skills taxonomy and a JSON
      city/state list. Normalises salary (number + currency + pa/pm), notice (days), experience
      (decimal years) and phone. Every field has a confidence (high/medium/low) and a reason;
      ambiguous input returns candidates and a warning instead of a guess
- [x] 4. Preview table: Field | Found value (editable) | Current form value | Confidence | tick,
      "Not found" rows, **Apply selected**, **Apply all high confidence**, **Cancel**
- [x] 5. Apply only fills the form (never saves); HR-typed values are replaced only when the row
      is ticked and **Replace** is ticked; "from quick fill" badges; **Undo quick fill** (skips
      fields edited afterwards); required-field validation, duplicate check and drafts unchanged
- [x] 6. Edge cases: Indian number formats, k / lakh / crore / LPA, ranges (maximum filled with a
      note, other readings offered), several candidates in one text (detected, never mixed),
      unknown words (listed as "not understood"), empty / very long / emoji / non-English text
- [x] 7. Tests: 613 engine tests (normalisers, every extractor with 15+ varied examples, styles,
      robustness), 18 API tests (permissions, rate limit, length limit, nothing saved, no text in
      logs), 50-line + 20-line hold-out accuracy fixtures with a report script
      (`python -m scripts.quick_fill_accuracy`) and regression floors, Playwright
      (`e2e/quick-fill.spec.ts`: type, Extract, edit, Apply, Undo, Replace, ambiguous salary,
      several candidates, edit dialog, save under the required-field rules)
- [x] 8. `USER-GUIDE.md` (with example sentences), `LICENSES.md` (no new dependencies)

Accuracy on the hand-labelled fixtures (`apps/api/tests/cv_engine/fixtures/`):

| Set | Fields expected | Correct | Accuracy | Wrong | Filled when it should stay empty | High-confidence precision |
| --- | --- | --- | --- | --- | --- | --- |
| 50 lines (used while tuning) | 301 | 298 | 99.0% | 0 | 0 | 100% |
| 20-line hold-out (first run, before any tuning) | 123 | 112 | 91.1% | 2 | 0 | 98.1% |
| 20-line hold-out (after fixing what it found) | 122 | 118 | 96.7% | 0 | 0 | 100% |

The hold-out was written after the 50-line set was tuned. Its first run is the honest estimate
for unseen text (about 91%); the later figure is no longer independent because the bugs it found
were fixed. Fields the text leaves ambiguous (two unlabelled salaries, for example) are expected
to stay empty and count as errors if they are filled.
