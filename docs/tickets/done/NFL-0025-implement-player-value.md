# NFL-0025 — Implement player value, ECR prior, and uncertainty handling

- Status: Done
- Resolution: Done
- Phase: 4 — Baseline recommendation engine
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0008, NFL-0024

## Canonical sources

- [Recommendation Engine](../../modeling/recommendation-engine.md#player-value)
- [Data and Player Identity](../../data/data-and-identity.md#initial-coverage-and-freshness)

## Outcome

A context-independent, versioned player value combines normalized projection and permitted market prior while representing freshness and uncertainty explicitly.

## Scope

Implement the configurable 65% own-model/35% ECR baseline, dispersion/movement uncertainty where available, and the approved missing/stale-market fallback.

## Acceptance criteria

- [x] Market consensus is neither the sole ranking nor silently treated as zero when absent.
- [x] Model, market, normalization, freshness, and uncertainty contributions are independently inspectable.
- [x] The same inputs and parameter version produce identical values.
- [x] Historical production already used by projections is not counted again.

## Validation

- [x] `test_valuation.py` covers fresh, stale, missing, dispersed, moving, invalid, and deterministic market inputs.
- [x] The fixture explicitly shows the 65/35 blend ranking differently from conflicting own-model-only and ECR-only rank orders.

## Completion summary

Implemented versioned context-independent valuation with an explicit 65/35 projection/ECR blend,
missing/stale fallback, inspectable dispersion/movement uncertainty, and no raw historical input.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Completed by Codex.
