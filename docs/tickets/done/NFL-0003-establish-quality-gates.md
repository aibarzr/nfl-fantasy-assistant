# NFL-0003 — Establish repository quality gates and reproducible commands

- Status: Done
- Resolution: Done
- Phase: 0 — Scaffolding
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: NFL-0001, NFL-0002

## Canonical sources

- [Development and Quality Guide](../../engineering/development.md#quality-gates)
- [Development and Quality Guide](../../engineering/development.md#definition-of-done)

## Outcome

One reproducible repository quality workflow covers all introduced backend, extension, contract, documentation, and build checks.

## Scope

Wire the concrete tools selected by the scaffolding tickets into local and CI checks, including drift detection where generation exists. Do not add substitute commands for tooling that has not been introduced.

## Acceptance criteria

- [x] Applicable formatting, lint, typing, unit-test, documentation-link, and build checks run in a documented order; there is no OpenAPI contract yet to check.
- [x] CI checks tracked-file drift and does not leave modifications behind.
- [x] Failure output identifies the component and command that failed.
- [x] `AGENTS.md` and the development guide contain the same exact supported toolchain commands.

## Validation

- [x] `./scripts/quality.sh all` passed on 2026-07-29: backend format/lint/type-check/tests/build, extension format/lint/type-check/tests/build, and local documentation links all passed. The source snapshot contains no Git metadata, so its local drift check reported a skip; CI runs the required Git-diff checks.
- [x] With uv deliberately unavailable from `PATH`, `./scripts/quality.sh backend` exited non-zero and printed both `[backend format]` and the exact failed uv command; no project file was modified.

## Completion summary

Added a single ordered repository workflow, local documentation-link validation, and a GitHub
Actions workflow that installs frozen dependencies, runs the workflow, and fails on tracked-file
drift. The command wrapper labels every component and command, making failures actionable.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-29 — Started by Codex after NFL-0001 and NFL-0002 completed.
- 2026-07-29 — Completed by Codex; validation evidence recorded above.
