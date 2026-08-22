# NFL-0028 — Build deterministic backtests and model-promotion checks

- Status: Done
- Resolution: Done
- Phase: 4 — Baseline recommendation engine
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0014, NFL-0027

## Canonical sources

- [Recommendation Engine](../../modeling/recommendation-engine.md#validation-and-promotion)
- [Development Guide](../../engineering/development.md#data-and-models)

## Outcome

Time-safe, reproducible backtests compare each model layer and the full engine with declared baselines and prevent unvalidated model promotion.

## Scope

Measure projection and decision metrics by position, format, slot/stage, rookies, and confidence against ECR-only, ADP-only, best-player, static VOR, dynamic VOR, and incremental full-engine baselines.

## Acceptance criteria

- [x] Backtest inputs cannot use information later than their simulated decision point.
- [x] Projection and decision layers have distinct metrics and reports.
- [x] Promotion requires reproducibility, passing tests, primary-metric improvement, acceptable segment regressions, and recorded limitations.
- [x] Results pin dataset, feature, model, parameter, and transform versions.

## Validation

- [x] `test_backtest.py` reruns the same pinned synthetic report and asserts equal metrics and rankings.
- [x] `test_backtest.py` demonstrates future-feature leakage, an incomplete baseline set, a non-improving primary metric, and material stage regression all block promotion.

## Completion summary

Implemented deterministic, time-safe projection and decision backtests with all declared
baselines, pinned data/model lineage, segmented reports, recorded limitations, and promotion
gates that reject primary or segment regressions.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Completed by Codex.
