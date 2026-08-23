# NFL-0045 — Activate Sleeper recommendation runtime

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0042, NFL-0043, NFL-0044

## Canonical sources

- [Data and Player Identity — Data lifecycle and runtime activation](../../data/data-and-identity.md#data-lifecycle)
- [Recommendation Engine — Draft decision baseline](../../modeling/recommendation-engine.md#draft-decision-baseline)
- [Architecture overview](../../architecture/overview.md)
- [Development workflow](../../engineering/development.md)

## Outcome

Publish the immutable projection and valuation inputs required by the verified Sleeper prepared pool, then generate and persist a current, reproducible Top-N recommendation snapshot after trusted Sleeper draft-state changes.

## Context

NFL-0044 activates only prepared-pool identity facts. Its baseline score cannot safely recreate the separate projection, valuation, uncertainty, and market inputs required by the approved recommendation model. This ticket retains those typed offline outputs and uses canonical availability and draft state to recompute dynamic VOR and ranking at runtime.

## In scope

- A checksum-pinned offline recommendation-input Parquet artifact coupled to the current prepared pool.
- Runtime validation and reconstruction of typed projection/value inputs without source-shaped records.
- Recalculation and persistence of a recommendation snapshot after trusted initialization, event ingestion, and reconciliation.
- Documentation and tests for provenance, unavailable legacy datasets, and stale/unsafe draft states.

## Out of scope

- Changing the recommendation model, adding simulation, or sourcing a new market feed.
- Extension presentation or polling changes.
- Backfilling an immutable version that does not contain the new artifact.

## Acceptance criteria

- [x] A newly published current pool contains the selected prepared players and the exact offline projection/valuation inputs required for deterministic ranking.
- [x] A crosswalk-published Sleeper runtime dataset validates that artifact and publishes a current recommendation snapshot only from active, fully resolved canonical state.
- [x] Dynamic VOR and roster-aware Top-N are recalculated when trusted Sleeper draft state changes, with version and source-time provenance persisted.
- [x] Runtime reports recommendations unavailable for legacy datasets that lack the artifact, without weakening identity activation.
- [x] Tests and canonical documentation cover the artifact, activation gates, and generated snapshot behavior.

## Validation

- [x] `uv --directory backend run ruff format --check .`, `ruff check .`, `mypy src tests`, and `pytest` passed (105 tests).
- [x] `./scripts/quality.sh docs` and `git diff --check` passed; final full quality/build and tracked-drift checks run after commit.
- [x] Confirmed the change contains no generated, local, restricted, or sensitive artifacts.

## Completion summary

Published `prepared_recommendation_inputs.parquet` with the prepared pool, including the typed
projection/value outputs used by the approved ranking model. Crosswalk publication re-pins that
artifact to its derived immutable version. Runtime activation validates one-to-one coverage and
provenance, then uses canonical availability and accepted picks to recompute dynamic VOR,
roster-aware ranking, explanations, warnings, and a current recommendation snapshot after trusted
Sleeper initialization, observations, and reconciliation. Legacy crosswalk versions retain safe
identity activation but report recommendation runtime unavailable. Synthetic unit/API tests cover
the artifact lifecycle, validation, and current snapshot refresh.

## History

- 2026-08-23 — Created in progress.
- 2026-08-23 — Completed with immutable typed recommendation inputs, derived-version re-pinning,
  canonical-state snapshot generation, and legacy safe-stop behavior.
