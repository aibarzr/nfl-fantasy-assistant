# NFL-0044 — Activate Sleeper runtime dataset

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0018, NFL-0039, NFL-0042, NFL-0043

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#non-functional-requirements)
- [Architecture Overview](../../architecture/overview.md#backend)
- [Data and Player Identity](../../data/data-and-identity.md#data-lifecycle)
- [Offline Data Contract](../../data/offline-data-contract.md#publication-and-pinning)
- [Protocol](../../contracts/protocol.md#approved-provider-expansion)
- [Development Guide](../../engineering/development.md#quality-gates)

## Outcome

The local backend can activate one checksum-verified published Sleeper dataset at startup, persist
only its exact prepared-pool mappings as draftable internal assets, report truthful data/identity
readiness, and reject a Sleeper draft request pinned to another dataset or feature version.

## Context

NFL-0042 and NFL-0039 published a local immutable prepared pool and a derived crosswalk version,
while NFL-0043 built the extension handoff that is blocked on local runtime readiness. Those
offline artifacts are not automatically runtime state: the backend currently has no loader and
therefore cannot resolve a valid live provider ID. This ticket promotes the validated artifact
through the backend data boundary without exposing raw nflverse or Sleeper records to the domain.

## In scope

- Load one explicit immutable dataset-version directory only after manifest checksum, typed prepared
  pool, typed Sleeper external-ID mapping, and prepared-pool coverage validation.
- Create only exact, resolved Sleeper mappings for prepared assets in the local repository; retain
  internal IDs, positions, provider IDs, and structural team-defense team code, never source names
  or raw payload fields.
- Make backend data and identity diagnostics reflect the activated runtime dataset, and fail closed
  for a Sleeper initialization whose dataset/feature/model pin is incompatible.
- Add an explicit local `serve --prepared-dataset` operation and synthetic tests for valid load,
  checksum/mapping/coverage failures, restart idempotency, and API enforcement.

## Out of scope

- Rebuilding or altering a published dataset, new data sources, provider calls, or raw-data import.
- Polling, reconciliation scheduling, recommendation-runtime activation, or the end-to-end browser
  acceptance fixture.
- Inferring a provider player identity from its name, team, or position.

## Acceptance criteria

- [x] The loader accepts only a complete checksum-verified immutable published version and maps all
  prepared assets exactly once through its Sleeper crosswalk.
- [x] Activated assets retain no raw provider record or display-name fallback, and every DEF has a
  validated structural team identity.
- [x] The backend reports ready data/identity only after successful activation and rejects a
  conflicting Sleeper session pin before canonical state mutation.
- [x] The extension’s initialization gate accepts ready data/identity while recommendation
  unavailability remains explicit and non-current.
- [x] Synthetic tests and operational documentation cover normal and material failure paths.

## Validation

- [x] Run applicable backend, extension, OpenAPI, and documentation checks.
- [x] Confirm no local dataset, real provider ID, source payload, or generated artifact is committed.

## Blocker

None.

## Completion summary

Added a runtime loader for one explicit checksum-verified Sleeper crosswalk-published dataset
directory. It validates the complete manifest, typed prepared pool, exact external-ID table, and
prepared-pool coverage, then persists only the 300 prepared assets' resolved Sleeper identities.
`DEF` entries require an exact structural team code; no raw response, display name, or mapping
outside the prepared pool reaches runtime state. The `serve --prepared-dataset` option activates
this boundary, diagnostics report ready data/identity, and Sleeper draft creation rejects missing
or mismatched dataset/feature/model pins before a draft is written. Recommendation availability
remains explicitly unavailable pending a separately sufficient runtime recommendation input.

Backend formatting/lint/type/build/OpenAPI checks and 102 tests passed; extension formatting,
lint, type-check, build, and 50 tests passed; docs and fixture validation passed; `git diff --check`
passed. The final tracked-drift check remains expected to fail until the active work is committed;
no generated or sensitive local artifact was added.

## History

- 2026-08-23 — Created and started to promote NFL-0042/NFL-0039's immutable local artifacts into
  the backend runtime boundary, separately from recommendation activation and live polling.
- 2026-08-23 — Completed with checksum/schema/coverage safe stops, runtime repository activation,
  exact version-pin enforcement, synthetic API coverage, and explicit operator startup guidance.
