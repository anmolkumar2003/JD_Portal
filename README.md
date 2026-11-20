# HR Recruitment Portal (ATS)

Monorepo for the HR Recruitment Portal. The specification lives in [`docs/SPEC.md`](docs/SPEC.md);
agent rules live in [`.cursor/rules/`](.cursor/rules).

| Path        | What                                                                              |
| ----------- | --------------------------------------------------------------------------------- |
| `apps/web`  | Next.js 14 (App Router), TypeScript strict, Tailwind, shadcn/ui, TanStack Query  |
| `apps/api`  | FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, Celery, Redis               |
| `docs/`     | Spec, split docs, ADRs                                                           |

## Prerequisites

- Docker Desktop with Docker Compose v2
- Optional, for running tools outside Docker: Python 3.11+, Node 20+, `pre-commit`

## Quick start

```bash
cp .env.example .env          # then change the passwords in .env
docker compose up --build     # or: make up  (detached)
make migrate                  # in a second terminal, once the stack is up
```

If a port is already in use on your machine, change the matching `*_PORT` variable in `.env`.
If you change `API_PORT`, also change `NEXT_PUBLIC_API_URL` to match.

## Services

| Service       | URL                                                  | Notes                                     |
| ------------- | ---------------------------------------------------- | ----------------------------------------- |
| Web           | http://localhost:3000                                | Home page shows "API connected"           |
| API docs      | http://localhost:8000/docs                           | Swagger UI; ReDoc at `/redoc`             |
| API health    | http://localhost:8000/health                         | 200 when DB and Redis are up, 503 if not  |
| MinIO console | http://localhost:9001                                | Log in with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`; bucket `cvs` is created automatically |
| Mailpit UI    | http://localhost:8025                                | Catches all outgoing email (SMTP on 1025) |
| PostgreSQL    | `localhost:5432`                                     | pgvector image; `vector` and `pg_trgm` enabled by migration `0001` |
| Redis         | `localhost:6379`                                     | DB 0 app, DB 1 Celery broker, DB 2 results |

MinIO no longer publishes community images to Docker Hub, so the stack uses Chainguard's
`cgr.dev/chainguard/minio` builds. Mailpit replaces MailHog (same ports, native on Apple Silicon).

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
| `make seed`    | Placeholder until the auth and data-model slices land    |

`make test` and `make lint` run in one-off containers and do not need the stack running.

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
