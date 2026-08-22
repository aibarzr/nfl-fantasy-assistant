# NFL-0001 — Scaffold backend toolchain and package structure

- Status: Done
- Resolution: Done
- Phase: 0 — Scaffolding
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: None

## Canonical sources

- [Development and Quality Guide](../../engineering/development.md#toolchain-status)
- [Architecture Overview](../../architecture/overview.md#backend)

## Outcome

A minimal Python backend skeleton with pinned tooling, explicit architectural boundaries, and reproducible development commands.

## Scope

Introduce the chosen Python/uv project configuration, backend package boundaries, supported runtime version, formatting, linting, typing, and test framework. Record exact commands in the development guide and `AGENTS.md`.

## Acceptance criteria

- [x] Backend packages preserve API, application/domain, data/model, and persistence dependency direction.
- [x] Runtime and development dependencies are pinned through the selected lockfile.
- [x] Exact install, format, lint, type-check, test, and backend build/run commands are documented and verified.
- [x] A minimal test proves the package can be imported without coupling domain code to FastAPI or persistence.

## Validation

- [x] `uv --directory backend sync --all-groups --frozen`, formatting, lint, type-check, tests,
  build, and `uv --directory backend run python -m nfl_fantasy_assistant --help` pass on
  2026-07-29.
- [x] `.gitignore` excludes tool environments, build output, caches, local data, tokens,
  databases, and logs; no such artifact is tracked.

## Completion summary

Added a Python 3.14.4/uv 0.12.0 backend package with a committed `uv.lock`, pinned resolved
dependencies, Ruff, mypy, pytest, and Hatchling build configuration. The package establishes API,
application, domain, data/model, and persistence boundaries; its import-boundary test verifies
that domain code remains independent of FastAPI, SQLite, and data-library imports.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-29 — Started by Codex.
- 2026-07-29 — Completed by Codex; validation evidence recorded above.
