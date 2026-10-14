# Runbook

## Local development

**Docker (everything):**

```bash
make up       # postgres, redis, migrations, api :8000, worker, dashboard :5173
make seed     # admin@leadforge.local / admin-change-me-123, reviewer@leadforge.local / reviewer-change-me-123
make logs
make down
```

**Without Docker** (needs Postgres 16 and Redis running locally, plus `uv` and Node 22):

```bash
make install
cp .env.example .env    # optional; defaults point at localhost
make migrate seed
make dev-api            # http://localhost:8000/api/docs
make dev-worker
make dev-dashboard      # http://localhost:5173
```

## Checks

`make check` runs what CI runs: ruff, prettier, eslint, mypy, tsc, pytest, vitest.
Tests use SQLite by default; set `TEST_DATABASE_URL` to run them against Postgres.

## Schema changes

1. Edit models in `api/leadforge/models/`.
2. `make migration m="describe change"` and review the generated file.
3. `make migrate`. CI runs upgrade → downgrade → upgrade → `alembic check`.

## Users

Admins can create reviewers in the API (`POST /api/users`). Rotate the seeded dev
passwords before exposing any environment.

## Dead-lettered jobs

`GET /api/jobs?status=dead` lists them with the last error.
