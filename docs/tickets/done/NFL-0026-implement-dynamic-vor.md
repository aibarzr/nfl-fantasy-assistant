# NFL-0026 — Implement dynamic replacement level and VOR

- Status: Done
- Resolution: Done
- Phase: 4 — Baseline recommendation engine
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0021, NFL-0025

## Canonical sources

- [Recommendation Engine](../../modeling/recommendation-engine.md#draft-decision-baseline)
- [Domain Model](../../domain/domain-model.md#scoring-and-draft-calculations)

## Outcome

Dynamic replacement values and VOR respond deterministically to league size, starting/flex demand, bench demand, current availability, and accepted picks.

## Scope

Keep replacement/VOR separate from projection and later contextual draft scoring. Do not encode universal positional replacement constants.

## Acceptance criteria

- [x] Replacement changes appropriately across 10/12 teams, roster slots, flex/superflex, bench demand, and draft state.
- [x] VOR consumes prepared player value rather than raw historical rows.
- [x] Available-player and roster inputs are canonical backend derivations.
- [x] Calculation components and configured parameters are reproducible and independently testable.

## Validation

- [x] `test_replacement.py` covers 10/12-team model scenarios, position demand, depleted/drafted
  pools, flex, superflex, and bench variants. Public MVP initialization remains 8-team only.
- [x] Dynamic replacement is compared with a declared starter-only static baseline.

## Completion summary

Implemented reproducible dynamic replacement demand and VOR over valued available players,
including direct, flex, bench, and accepted-draft positional demand components.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Completed by Codex.
