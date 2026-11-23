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
