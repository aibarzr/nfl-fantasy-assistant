# NFL-0010 — Build curated player and weekly-data transformations

- Status: Done
- Resolution: Done
- Phase: 2 — Data foundation
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0009

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#canonical-tables)
- [Architecture Overview](../../architecture/overview.md#offline-versus-live-processing)

## Outcome

Deterministic offline transforms produce stable, typed curated player and player-week tables from versioned source snapshots.

## Scope

Define implemented schemas for `players` and `player_week_features`, normalize source fields into stable football semantics, and retain lineage without exposing nflverse records outside the data layer.

## Acceptance criteria

- [x] Schemas, keys, required fields, units, null semantics, and lineage are versioned.
- [x] The same manifests and transform revision reproduce identical curated outputs.
- [x] Uniqueness, referential integrity, range, season/week, coverage, and missingness checks fail visibly.
- [x] Live runtime is not required to download or transform historical inputs.

## Validation

- [x] Fixture-sized player/player-week input is transformed and written as typed Parquet in
  `backend/tests/test_data_foundation.py`.
- [x] Tests cover duplicate keys, invalid share/range and season/week data, missing foreign players,
  and coverage thresholds; quality tooling passed on 2026-07-30.

## Completion summary

Implemented schema-versioned stable `players` and `player_week_features` Parquet transforms with
explicit football units/null semantics, source-manifest lineage, deterministic sorting, and visible
validation. The runtime-facing future layers receive stable records rather than nflverse rows.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex; validation evidence recorded above.
