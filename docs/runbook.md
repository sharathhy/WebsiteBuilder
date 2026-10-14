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

## Demo without any keys

`make demo` (or `python -m leadforge.cli demo --cities bengaluru,austin --categories
dentists --max-results 60` from `api/`) runs discover, enrich, audit, generate, gate and
draft in-process against the fictional mock world and prints a summary. Every business
is called "Sample ..." on a `.example` domain, so nothing can be mistaken for a real one.
Previews are written to `STORAGE_DIR/previews/` and served by the API at `/previews/`.
Mock emails that a human approves land in `STORAGE_DIR/outbox/` as JSON.

Set `SITE_BUILDER=next` to build previews with the animated Next.js template (needs
`npm ci` in `templates/site`, about 25 s per site), `static` for the fast HTML fallback,
or `auto` to use Next when it is installed.

## Going live (each step costs money or reaches real people: do them deliberately)

1. **Agency details:** fill in `config/agency.yaml` (sender name, sending address,
   postal address, booking link, prices). Sending is refused while any field says TODO.
2. **Budget:** set `monthly_budget_usd` and optional `provider_budgets_usd` in the same
   file. Paid calls stop with a dead-lettered job once the cap is reached.
3. **Keys** in the environment (never in files): `GOOGLE_PLACES_API_KEY`,
   `GOOGLE_PSI_API_KEY`, `ANTHROPIC_API_KEY`, `VERCEL_TOKEN`, `RESEND_API_KEY`,
   `RESEND_WEBHOOK_SECRET`, `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY`. Then set
   `MOCK_APIS=false`. A provider without a key stays mocked.
4. **Sending domain:** verify SPF, DKIM and DMARC for the sending domain in Resend, and
   point Resend's webhook at `POST /api/webhooks/email` (bounces and complaints suppress
   the address automatically).
5. **Public URL:** set `PUBLIC_BASE_URL` to the API's public HTTPS address, because
   unsubscribe links and contact forms point there.
6. Start with one city and one category, review the drafts, and keep
   `EMAIL_DAILY_LIMIT` low (default 40) while the domain warms up.

## Daily operation

- **Approvals** (dashboard): edit, approve or reject each draft. Approved emails still
  re-check suppression, the daily limit and agency details at send time. Follow-ups on
  day 3 and 7 are created as new drafts that also need approval, and stop automatically
  after a reply, unsubscribe, bounce, or a won/lost mark.
- **WhatsApp and call scripts** are never sent automatically: copy, send yourself, then
  mark sent.
- **Manual review** sites (failed the quality gate 3 times) show every attempt's score;
  use Regenerate after changing the template or spec.
- **Contact forms** on previews store messages in `form_submissions` and never forward
  them to the business while the site is only a preview.

## Maintenance jobs (worker cron)

- every 15 minutes: `send_due` sends approved emails that are due.
- 03:00 daily: expire previews older than `PREVIEW_TTL_DAYS` (30), re-audit scores older
  than 30 days, refresh Places data older than 30 days (Google caching terms).

## Monitoring

- `GET /health/ready` checks Postgres and Redis.
- `GET /api/metrics` (admin token) exposes job, lead, site and draft counts and month spend
  in Prometheus text format.
- Every response carries `X-Request-ID`, which also appears in the JSON access log.
- Set `SENTRY_DSN` to report errors.

## Dead-lettered jobs

The Analytics page lists them with the last error and a Retry button (admin), as does
`GET /api/analytics/queues`. `POST /api/jobs/{id}/retry` re-queues one.
