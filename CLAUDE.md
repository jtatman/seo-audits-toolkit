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

### Planned (tracked in beads)
- **Phase 2** (`bd show seo-audits-toolkit-jtc`): replace `bert-extractive-summarizer`/torch/
  transformers with a current transformers pipeline call, bump the Python 3.8 (EOL) base image
  alongside it, bump Django 3.1.4 → 5.2 LTS, refresh the `yake` pin off its git commit.
- **Phase 3** (`bd show seo-audits-toolkit-zr2`): react-admin v3→v5 and MUI v4→v5 in `admin/`,
  after adding frontend smoke-test coverage (currently zero — `App.test.js` is unmodified CRA
  boilerplate).

## Build & Test

```bash
# Server (Django/DRF)
docker compose build server
docker compose run --rm --entrypoint python server manage.py test      # 24 smoke tests
docker compose run --rm --entrypoint python server manage.py migrate

# Admin (React/react-admin dashboard)
docker compose build dashboard
cd admin && yarn install && NODE_OPTIONS=--openssl-legacy-provider yarn build

# Full stack
cp .env-example .env   # fill in SECRET_KEY, POSTGRES_PASSWORD, etc.
docker compose up -d
```

## Architecture Overview

_Add a brief overview of your project architecture_

## Conventions & Patterns

_Add your project-specific conventions here_
