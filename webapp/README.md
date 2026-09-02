# OSAT webapp (Flask rewrite)

A from-scratch rewrite of the SEO audit tool as a single Flask app, replacing
the Django/DRF + react-admin split in `../server` and `../admin`. See
`CLAUDE.md` in the repo root for why. This directory is fully self-contained
and independent of the root `docker-compose.yml` - it can be built, run, and
torn down without touching the old stack.

## Status

All planned features are ported: auth, site management (the "add a website
to audit" flow the old dashboard never had), a unified **site crawl**
(discovers pages via sitemap.xml or a link-crawl fallback, then extracts
keywords, a summary for the top pages by link-degree, related-pages-by-topic,
and AI-search-visibility checks for every page), a single-page **extractor**
(headers/images/links for one URL), **security** scanning (passive headers +
optional wapiti deep scan), and **PageSpeed Insights**.

Keyword extraction and summarization are *not* standalone tools here - they
only run against a site's own crawled content, not arbitrary pasted text.
If you want a general-purpose keyword extractor or summarizer, use `yake`/
`transformers` directly; this is an SEO tool.

**PageSpeed Insights needs a `PSI_API_KEY`** set in `.env` (a Google Cloud
API key - the API has zero free/anonymous quota) or every scan will fail
with a clear error explaining that. Every other feature works with no
extra configuration.

Cutting over from the old `../server`+`../admin` stack to this one (and
removing the old stack) hasn't happened yet - both currently run
independently side by side.

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
