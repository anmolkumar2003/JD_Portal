# Local Docker setup (development)

Use this for day-to-day development on the Mac Mini. Production/tunnel flow is in [PRODUCTION-DEPLOYMENT.md](./PRODUCTION-DEPLOYMENT.md).

## Prerequisites

- Docker Desktop (or compatible Engine + Compose v2) running on Apple Silicon
- Git clone of this repo; work from `hr-portal/`
- ~4–6 GB free RAM recommended while the stack is up

## First start

```bash
cd hr-portal
cp .env.example .env
# Optional: strengthen JWT_SECRET / passwords even for local use
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.cli.init_admin
# Optional demo data (APP_ENV=development only):
# docker compose exec api python -m app.cli.reference_data
# make seed-demo
```

Or: `make up` then `make migrate` / `make init-admin`.

## Published ports (dev only)

| Service | Host port (default) |
| ------- | ------------------- |
| Web | `3000` |
| API | `8001` → container `8000` |
| Postgres | `5432` |
| Valkey | `6379` |
| MinIO API / console | `9000` / `9001` |
| Mailpit UI / SMTP | `8025` / `1025` |

Open: [http://localhost:3000](http://localhost:3000) · API health [http://localhost:8001/health](http://localhost:8001/health) · Mailpit [http://localhost:8025](http://localhost:8025)

> Production compose does **not** publish DB/Valkey/MinIO. Do not copy dev port publishing into prod.

## Useful commands

```bash
make logs s=api
make test-api          # pytest in API container (needs stack or test DB)
make test-web
make backup            # backups/manual/<stamp>
make down              # stop (add v=1 only if you intend to wipe volumes)
```

## CV processing locally

Ensure `worker` is up (`docker compose ps`). Upload a CV; if status stays pending, check `make logs s=worker` and use **Reprocess** on the document.

## Feature flags

All `ENABLE_*=false` by default. Disabled modules return **404** for every HTTP method.
