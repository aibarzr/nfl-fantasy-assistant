# NFL-0036 — Finalize packaging, operations, backup, and release procedures

- Status: Backlog
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Unassigned
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: NFL-0003, NFL-0035

## Canonical sources

- [Operations Runbook](../../operations/runbook.md#installation-and-startup-checklist)
- [Operations Runbook](../../operations/runbook.md#release-and-rollback)

## Outcome

The runbook contains exact tested installation, startup, readiness, diagnosis, recovery, backup/export/reset, packaging, upgrade, and rollback procedures for the accepted local MVP.

## Scope

Replace every placeholder with actual supported commands, versions, configuration keys, paths, compatibility identifiers, and safe operational procedures; produce a reproducible extension package with minimal permissions.

## Acceptance criteria

- [ ] A clean supported machine can follow the documented steps through ready backend and loaded extension.
- [ ] Recovery covers page/worker/backend restart, missed pick, unknown player, adapter failure, and stale data without manual database editing.
- [ ] Backup/export excludes secrets and redacts identifiers; reset names an explicit target, confirms, and reports recoverability.
- [ ] Release/rollback records application, API, schema, extension, model, feature, and dataset compatibility and uses tested migrations/backups.

## Validation

- [ ] Perform a clean installation/readiness/recovery walkthrough using only documented commands.
- [ ] Build and inspect the release package, then exercise backup, upgrade, rollback, export, and targeted reset procedures.

## History

- 2026-07-29 — Created in Backlog.
