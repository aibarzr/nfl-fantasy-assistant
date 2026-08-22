# NFL-0016 — Implement SQLite repositories and forward migrations

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0015

## Canonical sources

- [Architecture Overview](../../architecture/overview.md#storage)
- [Development Guide](../../engineering/development.md#database-and-generated-artifacts)

## Outcome

SQLite repositories persist canonical domain state atomically and restore it after process restart through tested forward migrations.

## Scope

Choose and document the persistence implementation, create the initial schema/migration, repository interfaces and adapters for league, draft, picks, rosters, identity outcomes, metadata, and recommendation history.

## Acceptance criteria

- [x] Domain/application code depends on repository abstractions rather than SQLite details.
- [x] State transition and event outcome commit atomically; failure preserves the previous valid state.
- [x] Parameterized access and configured safe paths are used throughout.
- [x] Applied migrations are immutable and future changes have a documented forward-migration path.

## Validation

- [x] `test_sqlite_persistence.py` covers create/load/restart, rollback, identity/event conflicts,
  metadata, and unknown migration rejection; migrations 001/002 are append-only SQL.
- [x] Runtime settings restrict the database to a configured private state directory and `.gitignore`
  excludes databases and machine paths; full quality checks passed on 2026-07-30.

## Completion summary

Added parameterized SQLite repositories, forward migrations, atomic draft/event/reconciliation
commits, identity mappings, metadata, reconciliation history, and recommendation history.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex.
