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
