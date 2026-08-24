# NFL-0062 — Rank with explainable, validated injury risk

- Status: Done
- Resolution: Done
- Phase: 6 — Recommendation improvements
- Owner: Codex
- Created: 2026-08-24
- Updated: 2026-08-24
- Depends on: NFL-0059, NFL-0061

## Canonical sources

- [Recommendation Engine](../../modeling/recommendation-engine.md#layered-model)
- [Recommendation Engine](../../modeling/recommendation-engine.md#draft-decision-baseline)
- [Recommendation Engine](../../modeling/recommendation-engine.md#output-and-explanation)
- [Recommendation Engine](../../modeling/recommendation-engine.md#validation-and-promotion)
- [Domain Model](../../domain/domain-model.md#recommendationsnapshot)

## Outcome

Recommendations combine historical durability and a fresh current-status overlay through a
versioned, deterministic, explainable risk policy that is promoted only when it beats the
injury-neutral baseline without unacceptable segment regressions.

## Context

Observed current status and historical durability answer different questions. A current label is
not a recovery prognosis, and reserve status can retain draft value depending on league rules and
horizon. The first policy should expose risk and uncertainty without inventing unsupported injury
probabilities or automatically discarding players.

## In scope

- Define separate versioned inputs and component contributions for historical durability, current
  status severity, freshness, uncertainty, and any supported roster-slot context.
- Start with transparent status categories and warning/confidence behavior; numeric projection or
  ranking penalties require calibration evidence and an explicit promoted parameter version.
- Treat unknown, stale, conflicting, and unsupported status as uncertainty, never as healthy or a
  zero-risk score.
- Prevent automatic exclusion solely from questionable, doubtful, out, IR, PUP, or NFI labels
  unless canonical league eligibility rules and validated evidence justify a separately documented
  hard constraint.
- Return reason codes, human-readable explanations, freshness warnings, source observation time,
  overlay revision, feature/model/policy versions, and actual component effects in Top-N results.
- Backtest time-safe historical/prospective snapshots against the injury-neutral baseline by
  position, draft stage, status class, rookie/veteran, confidence, and league roster rules.

## Out of scope

- Medical advice, body-part recurrence modeling, recovery-date prediction, or narrative news
  interpretation.
- Opaque ML or simulation before the deterministic policy is independently validated.
- In-season lineup, waiver, drop, or trade decisions.

## Acceptance criteria

- [x] Canonical modeling and domain documentation define the policy, layer ownership, null/stale
  behavior, reproducibility inputs, explanations, and promotion gate before implementation.
- [x] Every status/durability adjustment is independently testable, versioned, present in component
  output, and reflected exactly by its explanation and warnings.
- [x] Missing or stale evidence reduces confidence or emits a warning according to the versioned
  policy and never fabricates health, prognosis, or a market signal.
- [x] Deterministic replay with stored draft state, dataset/model/feature pins, and overlay revision
  reproduces ranks, scores, confidence, components, and explanations.
- [x] Promotion evidence compares warning-only and calibrated policies with the injury-neutral
  baseline and records coverage, calibration, ranking quality, and segment regressions; unsupported
  numeric adjustments remain disabled.

## Validation

- [x] Test each neutral status class, historical-durability band, stale/missing/conflict path,
  reserve-slot context, explanation, provenance, and deterministic replay.
- [x] Run projection and decision backtests plus `./scripts/quality.sh all`; record exact metrics and
  promoted or rejected parameter versions.
- [x] Confirm no generated, local, restricted, or sensitive artifacts were committed.

## Completion summary

Implemented `injury-risk-v1-warning-only`: historical durability and current status are explicit
components/reasons, but never affect draft score or exclusion. The policy lowers confidence for
unknown/non-healthy status and unknown/low durability; calibrated numeric ranking/projection
penalties remain disabled. The prepared input schema is v2 with a v1 reader for published legacy
datasets. Backtests now segment status, durability, and roster rules; no calibrated policy was
promoted because no admissible historical status outcome coverage exists. `./scripts/quality.sh all`
passed all format, lint, type, test, build, contract, and documentation stages (127 backend and 61
extension tests); its final tracked-file-drift check correctly reported this uncommitted worktree's
intended changes. No generated client was hand-edited and no raw provider records were added.

## History

- 2026-08-24 — Created in Backlog as the promotion gate for injury-aware draft recommendations.
- 2026-08-24 — Started after NFL-0059 and NFL-0061 completed.
- 2026-08-24 — Completed with warning-only confidence policy; calibrated ranking penalties remain disabled.
