# NFL-0027 — Implement explainable Top-N draft scoring

- Status: Done
- Resolution: Done
- Phase: 4 — Baseline recommendation engine
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0026

## Canonical sources

- [Recommendation Engine](../../modeling/recommendation-engine.md#draft-decision-baseline)
- [Recommendation Engine](../../modeling/recommendation-engine.md#output-and-explanation)

## Outcome

The deterministic draft engine ranks available eligible players using versioned VOR, urgency, scarcity, market, roster, and risk/upside components and returns faithful explanations.

## Scope

Implement normalized stage profiles, deterministic next-turn survival/urgency approximation, scarcity, roster fit, legal constraints, confidence, Top-N output, reason codes, and freshness warnings. Monte Carlo is excluded.

## Acceptance criteria

- [x] Initial round-stage weights and normalization are configured and versioned rather than embedded as magic constants.
- [x] Scarcity, urgency, VOR, roster fit, market, and risk/upside remain separately inspectable.
- [x] Every candidate includes rank, score, confidence, components, reasons, uncertainty/freshness, and model/feature/dataset versions.
- [x] Explanations derive from actual measured components and blocked state returns no falsely current result.

## Validation

- [x] `test_draft_ranking.py` covers early/middle/late stages, next-turn distances, roster
  pressure, ties, blocked state, drafted-player filtering, and deterministic replay; stale warnings
  flow from valuation/projection inputs.
- [x] Ranking rejects duplicate/drafted availability and requires canonical roster-position data.

## Completion summary

Implemented versioned deterministic Top-N scoring with faithful measured components, profiles,
reason codes, warnings, canonical filtering, and no Monte Carlo dependency.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Completed by Codex.
