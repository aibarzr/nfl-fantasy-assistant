# NFL-0024 — Implement deterministic position-specific and rookie projections

- Status: Done
- Resolution: Done
- Phase: 4 — Baseline recommendation engine
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0012, NFL-0013, NFL-0014

## Canonical sources

- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)
- [Data and Player Identity](../../data/data-and-identity.md#feature-foundation)

## Outcome

Versioned deterministic projectors produce expected fantasy points, floor, ceiling, confidence, and component contributions independently of draft context.

## Scope

Implement distinct QB, RB, WR, TE, and rookie baselines over prepared semantic features and explicit league scoring. NCAA modeling remains deferred.

## Acceptance criteria

- [x] Position models reflect the documented position-specific roles and PPR/scoring inputs.
- [x] Rookies use the configured ECR/draft-capital/role/athletic prior rather than treating absent NFL history as negative evidence.
- [x] Every parameter and normalization set is versioned and explanations match actual contributions.
- [x] Projection code has no dependency on draft session or current roster state.

## Validation

- [x] `test_projection.py` covers QB/RB/WR/TE behavior, rookie priors, scoring variants,
  missing/stale inputs, parameter validation, and deterministic replay.
- [x] Dependency-free time-safe fixture metrics record MAE, RMSE, Spearman, and per-position
  segments through `models.metrics.projection_metrics`.

## Completion summary

Implemented versioned, deterministic position projectors over semantic features with explicit
scoring sensitivity, inspectable contributions, freshness warnings, rookie priors, and independent
projection metric calculation.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Completed by Codex.
