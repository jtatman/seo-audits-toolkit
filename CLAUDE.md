# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:1105d646 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

## Task & Memory Tracking

This project splits tracking across two systems - don't duplicate between them:

- **Beads (`bd`)** — plans and tasks. `bd ready` / `bd list` for current work, `bd show <id>` for
  detail. Modernization epics: `seo-audits-toolkit-jtc` (Phase 2: server) and
  `seo-audits-toolkit-zr2` (Phase 3: admin frontend).
- **Mnemoria** (`mnemoria/` dir; `mnemoria search "<query>"` or `mnemoria ask "<question>"`) —
  project memory: version-compatibility constraints, gotchas, and decisions discovered while doing
  this work (e.g. the Postgres major-version data-directory lock, the Jinja2/bokeh pin conflict).
  Check it before touching versioned infra or re-deriving something already learned the hard way.

## Modernization Log

Fork is ~5 years old; an ongoing effort is underway to bring docker-compose, dependencies, and app
code up to date. This is the running summary - full detail is in git history and mnemoria.

### Done
- **Phase 0** (commit `a39f881`, 2026-08-30): fixed docker-compose so it builds under WSL/Docker
  Desktop — the external Traefik network (never defined in this repo) and the `driver_opts`
  bind-mount volume format were the actual breakers. Dropped from-source Redis/Caddy builds for
  official images.
- **Phase 1** (commit `a39f881`, 2026-08-30/31): fixed 4 real security bugs in
  `server/core/settings.py` (hardcoded `SECRET_KEY` fallback, hardcoded `DEBUG=True`, ignored
  `ALLOWED_HOSTS`, hardcoded RDS hostname fallback), registered the `users` app, added the missing
  `permission_classes` on `internalLinks`'s viewset, bumped the confirmed-transitive-only packages
  (Pillow/PyYAML/requests/urllib3), added 24 DRF smoke tests (first test coverage in this repo),
  unblocked the admin build for Node 20/OpenSSL 3, bumped `POSTGRES_VERSION` 13→16 and
  `REDIS_VERSION` 6→7.
- **Phase 2** (`bd show seo-audits-toolkit-jtc`, closed, 2026-08-31): full server modernization in
  one pass — Python 3.8 (EOL) → 3.12, Django 3.1.4 → 5.2.17 LTS, every third-party Django app to
  current (djangorestframework/django-organizations/dj-rest-auth/django_celery_beat/django-filter/
  django_extensions), the whole numpy/scipy/pandas/scikit-learn/matplotlib stack, celery, and
  `yake` off its git-commit pin. Replaced `bert-extractive-summarizer` (which pinned 2020-era
  torch/transformers, pulling in the entire unused spacy 2.3.5 chain) with a direct
  `AutoModelForSeq2SeqLM`/`AutoTokenizer` call in `server/bert/src/bertSummarizer.py` — deliberately
  *not* `transformers.pipeline()`, which dropped the `"summarization"` task in transformers 5.x and
  silently loads the wrong (decoder-only) architecture if you reach for `"text-generation"` instead.
  `manage.py check`/`migrate`/`test` (24/24) all clean; full stack verified up. See mnemoria for the
  version-research trail and the gotchas hit along the way (apt-key gone on the newer Debian base,
  the packaging>=20.9 floor, etc).

- **Phase 3** (`bd show seo-audits-toolkit-zr2`, closed, 2026-08-31): admin frontend fully
  modernized — react-admin 3.14.1 → 5.15.1, MUI v4 → v6.5.0, React 17 → 19. Added 10 render smoke
  tests first (zero coverage existed before — `App.test.js` was unmodified CRA boilerplate).
  Discovered mid-migration that `react-scripts`/CRA itself (unmaintained since ~2023) can't
  reliably bundle current npm packages using modern `exports` maps (hit this with react-router 7.x
  and `@mui/utils` 9.x/6.x alike) — migrated the build tooling off `react-scripts` to **Vite 6 +
  Vitest 3** rather than perpetually downgrading dependencies to dodge an unmaintained bundler.
  That also meant renaming every `.js` file containing JSX to `.jsx` (Vite doesn't parse JSX in
  `.js` by default, unlike CRA) and dropped the old webpack4/5 OpenSSL-legacy-provider workaround
  entirely (Vite's esbuild/Rollup pipeline never touches that code path). Fixed the real
  react-admin v4/v5 breaking changes along the way: Redux fully removed from core (`useSelector` →
  `useSidebarState`/`<Admin theme/darkTheme>`), `basePath` prop removed, `DeleteButton`'s
  `undoable` → `mutationMode` (now defaults to undoable), `useVersion()` removed, custom Field
  components need `useRecordContext()` instead of prop injection, react-router v6's `Link`
  `to`/`state` split, MUI v5 theme shape (`overrides` → `components.X.styleOverrides`, `type` →
  `mode`), `makeStyles` → `sx`. All 10 tests pass, `yarn build` succeeds, verified via Docker build
  + full stack up + HTTP-level render check (no live browser was available in this sandbox for a
  visual check). See mnemoria for the full CRA→Vite checklist and the react-admin v5 gotchas.

- **Phase 4** (2026-08-31): functional audit + deadwood removal, done directly (not tracked as a
  beads epic — small enough to complete in one pass). Exercised every feature end-to-end against
  the live stack (not just smoke tests) and found/fixed 3 real bugs the dependency bumps had
  quietly introduced: `internalLinks` crashed on any site with zero discoverable internal links
  (`ZeroDivisionError`) and on bokeh's 2→3 API renames (`plot_width`→`width`,
  `Circle(size=...)`→`Scatter(marker="circle", size=...)`); `lighthouse` crashed because Google
  dropped the `"pwa"` category from Lighthouse's default output at some point (now defensive via
  `.get()` with an `"N/A"` fallback). Also found and fixed a real **shell-injection vulnerability**
  in both `security/tasks.py` and `lighthouse/tasks.py` — user-supplied `url` was concatenated into
  a `shell=True` subprocess string (arbitrary command execution, gated only by being any logged-in
  user); fixed via `subprocess.run([...])` argument lists. `security`'s scan backend
  (`httpobs-cli`, calling Mozilla's original HTTP Observatory API — discontinued 2024-10-31, hence
  the 502s) was replaced with `@mdn/mdn-http-observatory`'s self-hosted CLI, MDN's actively
  maintained successor — runs entirely locally now, no third-party API call at all
  (`bd show seo-audits-toolkit-7nm`, closed same day). Also dropped `ssh-audit` from
  requirements.txt/Pipfile — pinned but never actually imported anywhere in app code. Replaced the
  broken `init_data.json` onboarding fixture (hardcoded ContentType/Permission PKs, silently broken
  by Phase 2's migration-history changes) with an idempotent `manage.py seed_demo_data` command.
  Removed dead weight: `.docker/alpine/*` (zero references anywhere, leftover from a much older
  deployment topology), an accidentally-committed 462KB Lighthouse result dump in `shared/data/`,
  the unused `shared/logs/redis/` dir, stale `.gitignore` entries for services that don't exist
  (mysql, influxdb). Investigated the admin bundle's >500kB chunk warning — MUI splits cleanly into
  its own chunk (~530kB), but react-admin's UI layer imports MUI directly so splitting *that* out
  too produces a circular chunk; settled on the MUI-only split plus a 750kB warning threshold
  reflecting that real floor. README.md rewritten to match (correct login/init flow, dropped the
  `docker-compose pull` instruction since there's nothing to pull for this fork). `contribs/bert-summary` and `contribs/yake` (standalone, optional,
  never wired into root compose) were initially left alone rather than deleted outright — flagged
  for a decision instead of treated as obviously-orphaned deadwood. User confirmed both were
  redundant (bert-summary wrapped the same old bert-extractive-summarizer library just replaced in
  `server/bert`; yake wrapped the same `yake` library `server/keywords` already runs in-process) and
  both were removed (`bd show seo-audits-toolkit-e5c`, closed).

- **Phase 5** (2026-08-31): fixed a real production bug reported by the user — the dashboard loaded
  to react-admin's own error boundary ("Something went wrong / A client error occurred") on every
  visit, even though the API was directly reachable. Root-caused via a jsdom/Vitest reproduction
  (no live browser available in this sandbox) rather than the browser itself: `react-admin`
  resolved its own **nested, duplicate copy of `@mui/material` (v9.4.0)**, separate from the app's
  top-level pin (v6.5.0), because yarn classic doesn't dedupe across differently-formatted (if
  semver-overlapping) range strings in the lockfile. `MenuItemLink`'s internally-rendered MUI
  `MenuItem` therefore read a `MenuListContext` object from a different physical module instance
  than any `MenuList`/`Menu` the app rendered — "MUI: MenuListContext is missing" even though the
  component tree was structurally correct. Fixed by pinning `@mui/material`/`@mui/system`/
  `@mui/utils`/`@mui/icons-material` via a `resolutions` block in `admin/package.json`, forcing a
  single deduped copy tree-wide. (`admin/src/layout/Menu.jsx`'s `<Box>`→`<MenuList>` root-wrapper
  fix, made first, was necessary but not sufficient on its own — worth keeping regardless, since
  react-admin's own default `<Menu>` uses the same pattern.) Also fixed the frontend hardcoding
  `http://localhost:8000` in `App.jsx`'s dataProvider and `authProvider.js`'s login request — broke
  the moment `server`'s host-published port didn't match (exactly the user's case: remapped to 8001
  locally to dodge an unrelated container already on 8000). Real fix: `admin/Caddyfile` now reverse-
  proxies `/api/*` and `/dj-rest-auth/*` to `server:8000` over the internal Docker network (fixed
  internal port, unaffected by the host-side remap); the frontend calls relative same-origin paths
  by default (`admin/src/config.js`'s `API_URL`, empty unless `VITE_API_URL` is set), with a
  matching Vite dev-server proxy for `yarn start` outside Docker. Added a permanent regression test
  (`admin/src/App.test.jsx`) that renders the full `<App/>` → `Layout` → `Sidebar` → `Menu` chain —
  the gap that let this ship in the first place: Phase 3's 10 smoke tests only rendered isolated
  `List` components via `AdminContext`, never the real app shell, and Phase 3's own `App.test.js`
  had explicitly punted on a full-app render as "too fragile" (see git history for that comment) —
  in retrospect the wrong call, since it's exactly reproducible in jsdom and exactly where the bug
  was. Verified end-to-end against this sandbox's actual running stack (`osat-server` on host port
  8001, matching the user's setup): rebuilt `dashboard`, confirmed `curl localhost:3000/api/...` and
  `curl localhost:3000/dj-rest-auth/login/` proxy through to the server with identical responses to
  hitting `localhost:8001` directly, and a real login through the proxy returns a valid token.

- **Phase 6 (2026-09-01, in progress): full rewrite as a Flask monolith in `webapp/`.** After using
  the fully-modernized dashboard, the user found it unusable as a product, not just dated:
  react-admin's "Configuration" menu item was dead demo boilerplate never wired up, there was no
  way to add an organization/website from the dashboard at all (only through raw Django admin), and
  that gap cascaded into every audit-creation form failing with 400 "bad request" (their website
  picker had nothing to select). A competitive survey of open-source SEO audit tools (SEOnaut,
  open-seo-crawler) confirmed the feature combination is worth building — nothing OSS combines
  Lighthouse/PSI + sitemap + keywords + link graphs + security scanning — but that every
  actively-maintained comparable tool is a monolith with a server-rendered UI, not a decoupled
  API+SPA; that split bought nothing here and directly caused this session's MenuListContext
  duplicate-package bug and hardcoded-port bug (see Phase 5 above). Decision: rewrite as a Flask
  monolith in a new `webapp/` directory, run alongside the untouched old stack until it reaches
  parity (separate future cutover decision). User also pushed the infra footprint down mid-plan: no
  Postgres/Redis/Caddy by default, SQLite with a `DATABASE_URL` escape hatch to Postgres, hard cap
  of two containers (`web` + `worker`). Stack: Flask + SQLAlchemy + Flask-Login + Flask-WTF,
  **Huey** (not Celery) for background jobs — supports SQLite storage natively and its
  `@periodic_task` decorator replaces `django_celery_beat`'s DB-backed scheduler with plain code, no
  third "beat" container needed. Jinja2 + htmx frontend, no build step (htmx vendored locally, not
  CDN-loaded, to keep the app fully self-hosted with no runtime external dependency). Full plan
  (data model, feature port order, library swaps: PSI API replacing the dead `pyspeedinsights` and
  the Node `lighthouse` CLI, `ultimate-sitemap-parser` replacing pandas/manual XML parsing,
  `wapiti3`/in-process header check replacing the Node `mdn-http-observatory-scan` CLI) is at
  `~/.claude/plans/async-cooking-globe.md`. Skeleton milestone done and verified: app factory,
  `User`/`Site`/`SiteMembership` models (replacing `django-organizations` with a lightweight
  home-grown membership table), Flask-Login auth, Site create/list/detail pages (fixes the core
  "can't add an org" complaint from day one), Huey wiring with a working ping round-trip job,
  `webapp/Dockerfile` + self-contained `webapp/docker-compose.yml` (2 services). Verified via a real
  `docker compose build && up` — both containers healthy, register→login→create-site→list flow and
  the web→queue→worker job round trip all confirmed via curl against the actual running containers,
  not just local dev-server testing (caught and fixed a real CSRF-token bug this way: raw HTML
  `<form>`s need an explicit `{{ csrf_token() }}` hidden field with Flask-WTF's global
  `CSRFProtect`, which isn't automatic). Old `server`/`admin` stack untouched. Remaining phases per
  the plan: job infra is done, then port features cheapest-first (keywords → extractor/sitemap →
  internal links → security → lighthouse/PSI → bert summarizer), each ending with an actual browser
  walkthrough by the user, not just automated checks — direct response to this round's feedback that
  not seeing the real product sooner is what let the react-admin dashboard ship broken.

  Keywords (yake) ported next, first real feature end-to-end: `KeywordScan` model (site-scoped,
  the consistent `params`/`status`/`result` JSON shape from the plan), a `run_keyword_scan` Huey
  task, and site-scoped create/list/detail routes+templates, linked from the site detail page.
  Extracted the `get_owned_site_or_404` site-membership check into `app/utils.py` rather than
  duplicate it per blueprint, since the plan calls for the same check in every remaining feature.
  Verified via a full `docker compose build/up` round-trip (register → create site → submit text →
  scan finishes → keywords render, sensible output) — and that verification caught a real
  concurrency bug: `db.create_all()` inside `create_app()` ran once per gunicorn worker process,
  racing on `CREATE TABLE` against the same SQLite file on first boot (`table keyword_scan already
  exists`, worker failed to boot, gunicorn's arbiter recovered by respawning — silent in a health
  check, only visible in the container logs). Fixed with gunicorn's `--preload` flag, which imports
  the app once in the master process before forking workers, so `create_all()` runs exactly once.

  Extractor (headers/images/links) and sitemap ported next. Refactored the growing repetition
  across `KeywordScan`/`ExtractorScan`/`SitemapScan` into a `ScanMixin` (shared columns via
  SQLAlchemy `declared_attr`) and the matching job boilerplate into a `_run_scan(model, scan_id,
  work)` helper in `jobs.py` — worth doing once three near-identical classes/tasks existed rather
  than copy-pasting it three more times for the remaining features. `app/scrapers/` holds the
  actual scraping logic ported from the old Django app's `extractor/src/*.py` (headers/images/links
  walk the DOM via `bs4`+`lxml`, same as before); sitemap parsing swapped to
  `ultimate-sitemap-parser` per the plan, replacing the old pandas+manual-XML-recursion approach.
  Verified against real live sites, not just localhost fixtures: headers/images/links against
  python.org, sitemap crawl against djangoproject.com (1001 URLs, handled that site's sitemap
  variants 429-ing gracefully). That live testing caught a real performance problem the old Django
  app also had: LINKS extraction checks every unique link's status sequentially — 135 links on
  python.org's homepage took 37s serial. Fixed with a small `ThreadPoolExecutor` (20 concurrent
  requests) in `app/scrapers/links.py`, down to ~2.4s for the same page.

## Build & Test

```bash
# Server (Django/DRF)
docker compose build server
docker compose run --rm --entrypoint python server manage.py test      # 24 smoke tests
docker compose run --rm --entrypoint python server manage.py migrate
docker compose run --rm --entrypoint python server manage.py seed_demo_data  # admin/admin + demo org

# Admin (React/react-admin dashboard, Vite-based)
docker compose build dashboard
cd admin && yarn install && yarn build   # or `yarn test` (Vitest, 10 smoke tests)

# Full stack
cp .env-example .env   # fill in SECRET_KEY, POSTGRES_PASSWORD, etc.
docker compose up -d
```

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
