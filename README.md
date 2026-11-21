# HR Recruitment Portal (ATS)

Monorepo for the HR Recruitment Portal. The specification lives in [`docs/SPEC.md`](docs/SPEC.md);
agent rules live in [`.cursor/rules/`](.cursor/rules).

| Path        | What                                                                              |
| ----------- | --------------------------------------------------------------------------------- |
| `apps/web`  | Next.js 14 (App Router), TypeScript strict, Tailwind, shadcn/ui, TanStack Query  |
| `apps/api`  | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Celery, Redis               |
| `docs/`     | Spec, split docs, ADRs                                                           |

## Architecture (high level)

```
┌─────────────┐     HTTPS/JWT      ┌──────────────┐     SQLAlchemy      ┌────────────┐
│  apps/web   │ ◄────────────────► │   apps/api   │ ◄─────────────────► │ PostgreSQL │
│  Next.js 14 │   TanStack Query   │   FastAPI    │                     │  pgvector  │
└─────────────┘                    └──────┬───────┘                     └────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              ┌──────────┐         ┌──────────┐        ┌─────────────┐
              │  Redis   │         │  Celery  │        │ MinIO (S3)  │
              │ sessions │         │ CV parse │        │ CV storage  │
              └──────────┘         │  email   │        └─────────────┘
                                 └──────────┘
```

- **Web**: App Router route groups — `(public)` careers/login, `(portal)` jobs/candidates/dashboard.
  Server state via TanStack Query; shared types in `types/api.ts`.
- **API**: Router → service → model layering; RBAC and record-level job access on every portal route.
  Public careers apply is multipart to `POST /api/v1/public/jobs/{slug}/apply`.
- **CV engine**: Pure Python package under `apps/api/app/cv_engine/` (no FastAPI imports). Parsing,
  ATS check and JD match run in Celery (`process_document`); scores are advisory only.
- **Split docs**: [`docs/api.md`](docs/api.md), [`docs/ui.md`](docs/ui.md), [`docs/data-model.md`](docs/data-model.md),
  [`docs/cv-engine.md`](docs/cv-engine.md), [`docs/requirements.md`](docs/requirements.md).

## Prerequisites

- Docker Desktop with Docker Compose v2
- Optional, for running tools outside Docker: Python 3.11+, Node 20+, `pre-commit`

## Quick start

```bash
cp .env.example .env          # then change the passwords in .env
docker compose up --build     # or: make up  (detached)
make migrate                  # in a second terminal, once the stack is up
make seed                     # demo org, users, stages, jobs, ~30 candidates with scores
```

Then open http://localhost:3000/login and sign in with a demo account below.

If a port is already in use on your machine, change the matching `*_PORT` variable in `.env`.
If you change `API_PORT`, also change `NEXT_PUBLIC_API_URL` to match.

## Services

| Service       | URL                                                  | Notes                                     |
| ------------- | ---------------------------------------------------- | ----------------------------------------- |
| Web           | http://localhost:3000                                | Home page shows "API connected"; portal at `/login` |
| API docs      | http://localhost:8001/docs                           | Swagger UI; ReDoc at `/redoc`             |
| API health    | http://localhost:8001/health                         | 200 when DB and Redis are up, 503 if not  |
| MinIO console | http://localhost:9001                                | Log in with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`; bucket `cvs` is created automatically |
| Mailpit UI    | http://localhost:8025                                | Catches all outgoing email (SMTP on 1025) |
| PostgreSQL    | `localhost:5432`                                     | pgvector image; `vector` and `pg_trgm` enabled by migration `0001` |
| Redis         | `localhost:6379`                                     | DB 0 app, DB 1 Celery broker, DB 2 results |

MinIO no longer publishes community images to Docker Hub, so the stack uses Chainguard's
`cgr.dev/chainguard/minio` builds. Mailpit replaces MailHog (same ports, native on Apple Silicon).

## Demo accounts (local development only)

`make seed` creates the organization **Acme Corp** with one user per role. All demo users share
the password **`Demo@2026!`**. These credentials are for local demos only; never seed them into a
shared or production environment. Re-running `make seed` restores these passwords and clears any
lockout.

| Role           | Email                            | Can manage users | Jobs visible (record-level access)        |
| -------------- | -------------------------------- | ---------------- | ----------------------------------------- |
| Super Admin    | `superadmin@acme.example.com`    | Yes (any role)   | All                                       |
| HR Admin       | `hradmin@acme.example.com`       | Yes (not super_admin) | All                                  |
| Recruiter      | `recruiter@acme.example.com`     | No               | All                                       |
| Hiring Manager | `manager@acme.example.com`       | No               | Senior Backend Engineer, Frontend Engineer |
| Interviewer    | `interviewer@acme.example.com`   | No               | Senior Backend Engineer                   |

The seed also creates the default pipeline stages (Applied, Screening, Interview, Offer, Hired,
Rejected), two departments (Engineering, People Operations), two locations (Bengaluru HQ,
Remote (India)), three jobs with weighted required and preferred skills, and **30 demo candidates**
(`demo01@candidates.demo` … `demo30@candidates.demo`) with applications on the open engineering jobs,
parsed CV profiles, match scores, and a spread across pipeline stages. Re-running `make seed` is
idempotent for these rows.

## Auth overview

- `POST /api/v1/auth/login` returns a 15-minute access token (send as `Authorization: Bearer`)
  and sets a 7-day refresh token in an httpOnly cookie scoped to `/api/v1/auth`.
- `POST /auth/refresh` rotates the refresh token; `POST /auth/logout` revokes it (Redis denylist).
- Five wrong passwords lock the account for 15 minutes (HTTP 423, even with the right password).
- `POST /auth/forgot-password` emails a single-use, 30-minute reset token via Mailpit;
  `POST /auth/reset-password` accepts it. A reset page in the web app comes in a later slice.
- `GET/POST /api/v1/users` and `PATCH /users/{id}/role` are limited to super and HR admins.
- Role checks use `require_roles(...)`; job-level access uses `scope_jobs_query` /
  `ensure_job_access` in `app/core/deps.py`.

## Verifying this slice

```bash
API=http://localhost:8001/api/v1
login() { curl -s -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d "{\"email\":\"$1@acme.example.com\",\"password\":\"${2:-Demo@2026!}\"}"; }
```

1. **Login for each role**: sign in at http://localhost:3000/login with each demo account; the
   dashboard shows the name and role. Or: `login recruiter` returns `user.role = "recruiter"`.
2. **403 for a wrong role**:
   `TOKEN=$(login recruiter | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')`
   then `curl -i $API/users -H "Authorization: Bearer $TOKEN"` returns 403 with
   `{"error":{"code":"forbidden",...}}`. The same call with `hradmin` returns 200.
3. **Lockout**: run `login interviewer wrong` five times. The first four return 401, the fifth
   returns 423 `account_locked` with `locked_until`, and `login interviewer` (correct password)
   still returns 423. Run `make seed` to unlock.
4. **Password reset**: `curl -X POST $API/auth/forgot-password -H 'Content-Type: application/json' -d '{"email":"recruiter@acme.example.com"}'`,
   open http://localhost:8025 to read the token, then POST it to `$API/auth/reset-password`
   with `{"token": "...", "new_password": "..."}`.
5. **Seeded data**:
   ```bash
   docker compose exec postgres psql -U hrportal -d hrportal -c \
     "SELECT email, role FROM users ORDER BY role;" -c \
     "SELECT \"order\", name, type FROM pipeline_stages ORDER BY \"order\";" -c \
     "SELECT j.title, j.status, d.name AS dept, l.name AS location, jsonb_array_length(r.required_skills) AS req, jsonb_array_length(r.preferred_skills) AS pref FROM jobs j JOIN departments d ON d.id = j.department_id JOIN locations l ON l.id = j.location_id JOIN job_requirements r ON r.job_id = j.id;"
   ```
6. **Automated checks**: `make test-api` (with the stack up) runs the auth, RBAC, lockout,
   record-level access and jobs tests against a separate `<db>_test` database.

## Jobs module

- Portal: `/jobs` (filters, search, sort, pagination), `/jobs/new` (4-step form),
  `/jobs/{id}` (Details and Applicants tabs, Publish / Close), `/jobs/{id}/edit`.
- API: `GET/POST /api/v1/jobs`, `GET/PATCH /jobs/{id}`, `POST /jobs/{id}/publish|close`,
  `PUT /jobs/{id}/requirements|team`, plus read-only `GET /departments` and `GET /locations`.
- Public, no auth: `GET /api/v1/public/jobs` and `GET /api/v1/public/jobs/{slug}` (open jobs only).
- Recruiters, HR admins and super admins create and edit; hiring managers and interviewers only
  see jobs they are on the team for.

To verify:

1. Sign in as `recruiter@acme.example.com`, open **Jobs**, click **Create job**, fill in the
   four steps (a description is required to publish) and click **Save and publish**.
2. The detail page shows status **Open**, the slug (e.g. `my-new-job`) and a
   **View public listing** link.
3. Open `http://localhost:8001/api/v1/public/jobs/{slug}`: it returns the job without salary
   or team. Click **Close job** and the same URL returns 404.
4. Sign in as `manager@acme.example.com`: **Jobs** lists only the two jobs they manage and
   there is no **Create job** button.

## Careers site and applications

- Public pages (no login): `/careers`, `/careers/{slug}`, `/careers/{slug}/apply` (3 steps),
  `/careers/{slug}/applied?ref=…`.
- `POST /api/v1/public/jobs/{slug}/apply` (multipart): the CV must really be a PDF or DOCX
  (checked by file content) and at most 5 MB. A hidden honeypot field (`website`) stands in for
  a CAPTCHA, and each IP may apply 5 times per hour (Redis).
- Each application reuses the candidate with the same email (or creates one), starts in the
  "Applied" stage, gets a reference like `APP-2026-000001`, stores the CV in MinIO (`cvs`
  bucket), adds a `documents` row and a `parsed_profiles` row with status `pending`, and emails
  a confirmation.
- `GET /api/v1/documents/{id}/download-url` returns a signed link that expires in 5 minutes,
  for staff who can see the job.

To verify:

1. Open http://localhost:3000/careers, pick a job, click **Apply for this role**, complete the
   three steps with a real PDF or DOCX CV and submit. Note the reference number.
2. Mailpit (http://localhost:8025) shows "Application received: … (APP-2026-…)".
3. MinIO console (http://localhost:9001, login `minioadmin` / the `MINIO_ROOT_PASSWORD` in
   `.env`): bucket `cvs` contains `{org_id}/{candidate_id}/{document_id}.pdf`.
4. The new row:
   ```bash
   docker compose exec postgres psql -U hrportal -d hrportal -c \
     "SELECT a.reference_no, s.name AS stage, c.email, d.file_name, p.parse_status FROM applications a JOIN pipeline_stages s ON s.id = a.stage_id JOIN candidates c ON c.id = a.candidate_id JOIN documents d ON d.application_id = a.id JOIN parsed_profiles p ON p.document_id = d.id ORDER BY a.applied_at DESC;"
   ```

## Make targets

| Target         | Does                                                     |
| -------------- | -------------------------------------------------------- |
| `make up`      | Create `.env` if missing, build and start everything     |
| `make down`    | Stop the stack (`make down v=1` also deletes volumes)    |
| `make logs`    | Follow logs (`make logs s=api` for one service)          |
| `make migrate` | `alembic upgrade head` inside the running API container  |
| `make test`    | pytest for the API, type-check for the web app           |
| `make lint`    | Ruff + mypy (API), ESLint + Prettier (web)               |
| `make format`  | Auto-fix formatting in both apps                         |
| `make seed`    | Seed demo org, users, stages, jobs and 30 candidates     |

`make test` and `make lint` run in one-off containers. Database-backed API tests need Postgres up
(`make up`) and are skipped otherwise; they use a separate `<db>_test` database.

## Development notes

- **Hot reload**: `apps/api` and `apps/web` are bind-mounted; the API runs `uvicorn --reload`
  and the web app runs `next dev`.
- **Dependencies**: after changing `pyproject.toml` or `package.json`, run
  `docker compose up --build -V` so the image and the `node_modules` volume are rebuilt.
- **Migrations**: create one with
  `docker compose exec api alembic revision --autogenerate -m "message"`; never edit the DB by hand.
- **Celery**: the sample task `ping` lives in `app/workers/tasks.py`. Try it with
  `docker compose exec api python -c "from app.workers.tasks import ping; print(ping.delay().get(timeout=10))"`.
- **Logging**: the API and worker log one JSON object per line. Every request gets an
  `X-Request-ID` (accepted from the client if well-formed, otherwise generated), which is
  returned in the response header and included in every log line for that request.
- **Configuration**: all settings come from environment variables (`app/core/config.py`).
  `.env.example` values target tools run from your host; `docker-compose.yml` overrides the
  hostnames for containers.

## Pre-commit and CI

```bash
git init                      # if this is a fresh checkout
pip install pre-commit
(cd apps/web && npm ci)       # eslint/prettier hooks use the local node_modules
pre-commit install
pre-commit run --all-files
```

`.github/workflows/ci.yml` runs on pushes to `main` and on pull requests:

- **api**: ruff, ruff format check, mypy (strict), pytest with coverage, and an Alembic
  upgrade/downgrade round-trip against a pgvector Postgres service.
- **web**: ESLint, Prettier check, `tsc --noEmit`, `next build`.

## Playwright end-to-end (Phase 8)

With the stack up (`make up`, `make migrate`, `make seed`):

```bash
make test-e2e
```

Or locally (Node 20+ on the host):

```bash
cd apps/web
npm ci
npx playwright install chromium   # first time only
npm run test:e2e
```

`make test-e2e` runs the official Playwright Docker image against
`http://host.docker.internal:3000` (ensure `CORS_ORIGINS` includes that origin — the default
`.env.example` lists it). Sign-in uses `recruiter@acme.example.com` / `Demo@2026!`. Coverage:
careers apply, recruiter candidate list scores, Kanban stage moves, and rejection with reason.
Interview scorecard and offer approval tests **skip** until portal pages exist (APIs are ready).

CV parse eval against `apps/api/tests/golden/real/`:

```bash
docker compose exec api python scripts/eval_real_cvs.py
```

## Load testing (local)

A small async probe for list + apply throughput:

```bash
cd apps/api
python scripts/load_test_apply_and_list.py --list-requests 40 --apply-requests 5
```

Defaults: recruiter login, `GET /applications`, `POST /public/jobs/senior-backend-engineer/apply`
with minimal PDF bytes.

## Phase 8 demo readiness

After seed, you can demo: careers apply, recruiter Kanban on **Senior Backend Engineer** (scored
candidates), candidate profile **Match Analysis**, stage move / reject with reason, and dashboard
KPIs. Run Playwright and the load script above before a stakeholder walkthrough.
