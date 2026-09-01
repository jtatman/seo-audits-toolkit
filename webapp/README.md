# OSAT webapp (Flask rewrite)

A from-scratch rewrite of the SEO audit tool as a single Flask app, replacing
the Django/DRF + react-admin split in `../server` and `../admin`. See
`CLAUDE.md` in the repo root for why. This directory is fully self-contained
and independent of the root `docker-compose.yml` - it can be built, run, and
torn down without touching the old stack.

## Status

Skeleton only, so far: auth (register/login/logout) and site management
(the "add a website to audit" flow the old dashboard never had). No audit
features are ported yet - see the plan for the port order.

## Running it

```bash
cd webapp
cp .env-example .env   # then set a real SECRET_KEY
docker compose up --build -d
```

Visit [localhost:5000](http://localhost:5000), register an account, and add
a site.

Two containers only: `web` (the app) and `worker` (background job
processing via Huey). No Postgres, Redis, or reverse-proxy container ships
by default.

## Storage

SQLite by default - a single file in the `webapp-data` Docker volume, no
separate database container. For a real multi-user/production deployment,
set `DATABASE_URL` in `.env` to a `postgresql://user:pass@host:5432/dbname`
connection string instead (requires `psycopg2-binary`, not currently in
`requirements.txt` - add it if you use this).

For a long-term multi-instance deployment sharing one database, front
multiple installs with your own reverse proxy/load balancer (haproxy,
Caddy, nginx) pointed at a shared Postgres backend - nothing here assumes
or requires that topology, so it's on you to wire up if you need it.

## Local development without Docker

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
SECRET_KEY=dev DATABASE_URL="sqlite:////tmp/osat-dev.db" HUEY_DB_PATH="/tmp/osat-dev-huey.db" \
  .venv/bin/python wsgi.py
# in a second terminal, for background jobs:
SECRET_KEY=dev DATABASE_URL="sqlite:////tmp/osat-dev.db" HUEY_DB_PATH="/tmp/osat-dev-huey.db" \
  .venv/bin/huey_consumer app.jobs.huey
```
