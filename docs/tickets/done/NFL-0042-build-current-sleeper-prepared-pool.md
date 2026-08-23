# NFL-0042 — Build current Sleeper prepared-pool dataset

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0013, NFL-0038, NFL-0041

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#data-lifecycle)
- [Offline Data Contract](../../data/offline-data-contract.md#publication-and-pinning)
- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)
- [Source Inventory](../../data/source-inventory.md#approved-nflverse-through-nflreadpy)
- [Development Guide](../../engineering/development.md#quality-gates)

## Outcome

One local, immutable 2026 prepared dataset contains a data-backed, version-pinned, Sleeper-eligible
draft pool for the approved eight-team league configuration. It is suitable as the exact coverage
input to NFL-0039, but does not itself enable a live draft.

## Context

NFL-0039's mapping report has validated the local Sleeper catalog and reviewed mappings, but it
must prove that every asset in the actual prepared pool is mapped before publication. The project
has a current nflverse identity/roster snapshot and the completed neutral K/DEF scoring semantics,
but no immutable dataset version containing `prepared.parquet`.

## In scope

- Define a reproducible local build path from approved nflverse historical and current season-state
  snapshots to semantic features, data-backed projections, and deterministic prepared values.
- Preserve source-manifest lineage, scoring translation, feature/model versions, coverage and
  missingness checks in a staged, atomically published 2026 dataset.
- Use only candidates that are current-season eligible and exactly resolved in the reviewed Sleeper
  crosswalk; keep unavailable history, unsupported rookie evidence, and unmapped assets explicit
  rather than inventing values or identities.
- Include individual K and structural, season-valid DEF assets only when their required projection
  evidence is available under the configured field-goal and defensive-points-allowed rules.
- Produce a local operational command and synthetic tests for successful publication, incomplete
  lineage, insufficient position/scoring evidence, and an unmapped candidate.
- Run NFL-0039 validation against the resulting immutable version and record the result locally.

## Out of scope

- Publishing raw or prepared data to version control or an external service.
- A new historical, market-prior, or provider data source; FantasyPros remains excluded.
- Backend initialization, live Sleeper polling, or extension behavior changes.
- Treating missing player history, a name match, or a Sleeper catalog field as a projected value.

## Acceptance criteria

- [x] The build has a documented, deterministic local command and outputs a checksum-verified
  immutable version with `prepared.parquet` and complete manifest validation evidence.
- [x] Every prepared row has a resolved internal identity, an approved scoring-aware, data-backed
  value, and identical dataset/feature versions to its manifest.
- [x] The eight-team league context and observed Sleeper scoring configuration shape the pool; K
  and DEF fail closed if their required band evidence is incomplete.
- [x] The published pool is entirely covered by the checksum-pinned Sleeper crosswalk; NFL-0039
  validation either succeeds without unresolved/conflict mappings or reports the exact safe stop.
- [x] Synthetic tests cover publication and material failure paths without a network request or
  retained raw provider payload.
- [x] Canonical data, source-inventory, modeling, operational, and ticket documentation remain
  aligned; no generated, local, restricted, or sensitive artifacts are committed.

## Validation

- [x] Run applicable backend formatting, lint, type, test, build, documentation, and OpenAPI
  contract checks.
- [x] Re-run the build from the same local source snapshots and verify the immutable output and
  crosswalk coverage are reproducible.

## Completion summary

Published local immutable base version `2026-sleeper-prepared-v1` with 300 data-backed prepared
assets (55 QB, 70 RB, 80 WR, 41 TE, 31 K, and 23 DEF), feature version `3`, nine source manifests,
and checksum `41ef049b58cce11ae195579c32ae0a226f1785b0196d9f93ae049ad52296773b`. NFL-0039 then
validated all prepared assets and published the derived `2026-sleeper-crosswalk-v1` version. Both
versions and the neutral configuration remain under ignored local `data/` paths.

## History

- 2026-08-23 — Created and started after NFL-0041 completed; separates preparation/publication
  evidence from NFL-0039's identity-mapping result.
- 2026-08-23 — Implemented and tested the checksum-verified local build/publish path using
  approved 2022–2025 historical snapshots and 2026 roster state. The actual private neutral
  scoring configuration remains intentionally absent; blocked pending an authorized supported
  draft page rather than using a default.
- 2026-08-23 — Resumed after authorized read-only capture of the neutral eight-team configuration.
  Published the prepared base version and validated/published its Sleeper crosswalk derivative with
  full prepared-pool coverage and no conflicts.
