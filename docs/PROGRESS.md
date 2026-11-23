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

### Phase 4: search and filters

- [ ] Full-text and trigram search, filter popover, saved filters, jobs filters, Cmd+K

### Phase 5: dashboard, polish, responsive

- [ ] Charts, table and Kanban polish, design tokens, dark mode, responsive screenshots

### Phase 6: go-live package

- [ ] Production compose with Caddy, secrets script, SMTP, hardening, backups and restore drill,
      ClamAV, retention job, `DEPLOY.md`, `USER-GUIDE.md`
