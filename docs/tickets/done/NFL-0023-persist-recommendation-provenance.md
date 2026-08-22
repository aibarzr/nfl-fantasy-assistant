# NFL-0023 — Persist reproducible recommendation snapshots and provenance

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0016, NFL-0021

## Canonical sources

- [Domain Model](../../domain/domain-model.md#recommendationsnapshot)
- [MVP Specification](../../product/mvp-spec.md#non-functional-requirements)

## Outcome

Every published recommendation snapshot is durably associated with the canonical revision and all inputs and versions required to reproduce it.

## Scope

Persist pick context, available-set reference, candidate outputs/components, timestamp, league configuration, source updates, model/feature/dataset versions, and chosen action when later known.

## Acceptance criteria

- [x] A snapshot is committed before its response is presented as current.
- [x] The record identifies canonical revision, inputs, data/features/model versions, freshness, and candidate calculations.
- [x] Blocked or stale state cannot relabel an older result as current.
- [x] Stored inputs under the same versions reproduce candidate ordering and components.

## Validation

- [x] `test_recommendation_provenance_survives_restart_and_rejects_stale_or_blocked_state`
  covers persistence/restart, stale commit rejection, blocked state, deterministic candidate replay,
  and prior-current invalidation on a canonical state mutation.
- [x] Snapshots exclude credentials by model design; diagnostics reports only component readiness and
  API tests inspect secret-safe health/error output. Full quality checks passed on 2026-07-30.

## Completion summary

Added durable recommendation snapshots with pinned provenance and candidate components. Atomic
state changes invalidate an older current snapshot, while the API rejects blocked, reconciling, or
revision-mismatched results as non-current.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
