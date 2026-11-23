# HR Recruitment Portal

An internal, HR-only recruitment portal: jobs, candidates, CV parsing with advisory match
scores, pipeline, notes and interview ratings. There is no public sign-up and no candidate login;
the optional public careers site ships switched off.

The specification is [`docs/SPEC.md`](docs/SPEC.md); progress is tracked in
[`docs/PROGRESS.md`](docs/PROGRESS.md).

| Path       | What                                                                             |
| ---------- | -------------------------------------------------------------------------------- |
| `apps/web` | Next.js 14 (App Router), TypeScript strict, Tailwind, shadcn/ui, TanStack Query |
| `apps/api` | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Celery, Redis              |
| `docs/`    | Spec, split docs, licenses, audit                                               |

Everything is free and open source; see [`docs/LICENSES.md`](docs/LICENSES.md).

## Architecture

```
Browser ──► apps/web (Next.js) ──/api/v1 proxy──► apps/api (FastAPI) ──► PostgreSQL
                                                        │
                                           Redis ◄──────┼──────► MinIO (CV files)
                                                        │
                                              Celery worker: CV parsing, ATS check,
                                              match score, email
```

- The browser only talks to the web origin. Next.js forwards `/api/v1/*` to the API
  (`INTERNAL_API_URL`), so the refresh cookie is first-party. In production Caddy does the same.
- API layering is router → service → model, with role checks and record-level job access on
  every portal route.
- The CV engine (`apps/api/app/cv_engine/`) is plain Python. Scores are advisory: nothing is
  rejected or advanced automatically, and name, gender, age, photo and nationality are never
  scoring features.

## First-time setup (local)

Prerequisites: Docker Desktop with Compose v2.

```bash
cp .env.example .env    # then change every password and JWT_SECRET in .env
make up                 # build and start the stack
make migrate            # create the database schema
make init-admin         # run twice: once for the super_admin, once for the HR admin
```

`make init-admin` asks for email, name, role and a password (leave the password empty to get a
generated one, shown once). Reference data (pipeline stages, email templates, departments) is
created automatically and can be re-applied with `make reference-data`.

Open http://localhost:3000 and sign in. An account created with a generated or temporary
password must choose its own password on first sign-in. Further users are added in
**Settings > Users**.

## Services (development)

| Service       | URL                        | Notes                                                 |
| ------------- | -------------------------- | ----------------------------------------------------- |
| Portal        | http://localhost:3000      | Sign in at `/login`                                   |
| API docs      | http://localhost:8001/docs | Swagger UI                                            |
| Mailpit       | http://localhost:8025      | Catches every outgoing email in development           |
| MinIO console | http://localhost:9001      | `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from `.env` |

## Optional modules

All are off by default. When a flag is off its pages and menu items are hidden and its API
endpoints answer 404. Audit logging itself is always on.

| Flag                    | Module                                             |
| ----------------------- | -------------------------------------------------- |
| `ENABLE_PUBLIC_CAREERS` | Public careers site and apply form (`/careers`)    |
| `ENABLE_INTERVIEWS`     | Panel scheduling and calendar (simple ratings stay) |
| `ENABLE_OFFERS`         | Offer letters and approvals                        |
| `ENABLE_REQUISITIONS`   | Hiring requisitions                                |
| `ENABLE_AUDIT_UI`       | Audit log viewer                                   |

## Make targets

| Target                | Does                                                                     |
| --------------------- | ------------------------------------------------------------------------ |
| `make up` / `down`    | Start / stop the development stack (`make down v=1` deletes volumes)     |
| `make migrate`        | `alembic upgrade head`                                                   |
| `make init-admin`     | Create or reset an account interactively                                 |
| `make reference-data` | Add any missing stages, email templates and departments                  |
| `make backup`         | Database dump and CV bucket copy into `backups/manual/<timestamp>`       |
| `make seed-demo`      | Fake demo data; refuses unless `APP_ENV=development`, never automatic    |
| `make cleanup-demo`   | Delete all candidates, jobs and demo users, and empty the CV bucket      |
| `make lint`           | Ruff, ruff format, mypy (API); ESLint, Prettier, tsc (web)               |
| `make test-api`       | pytest against a separate `<db>_test` database                           |
| `make test-e2e`       | Playwright in an isolated throwaway stack (see below)                    |

### Demo data

`make seed-demo` loads three jobs (Senior Android Developer, Shopify Developer, Content
Writer), 30 fake candidates and one account per role on `@demo.example.com`. The demo password
comes from `DEMO_PASSWORD` or is generated and printed once. Never run it on a real install;
remove it again with `make cleanup-demo`.

### End-to-end tests

`make test-e2e` starts `docker-compose.e2e.yml`: its own project, network and in-memory
storage, with nothing published on the host. It builds the production web image, migrates, seeds
demo data with a password generated for that run, runs Playwright and removes the stack. The
development stack and `.env` are not touched.

## Development notes

- The API is bind-mounted and reloads on change. The web dev image is not bind-mounted; for hot
  reload run `cd apps/web && npm ci && npm run dev` on the host (it proxies to
  `http://localhost:8001`).
- After changing `pyproject.toml`, rebuild with `docker compose build api worker`.
- Create migrations with `docker compose exec api alembic revision --autogenerate -m "..."` and
  check for drift with `docker compose exec api alembic check`.
- Logs are JSON lines; every request carries an `X-Request-ID`.
- CV extraction quality can be compared across PDF libraries with
  `docker compose exec api python tests/golden/compare_pdf_backends.py`.
