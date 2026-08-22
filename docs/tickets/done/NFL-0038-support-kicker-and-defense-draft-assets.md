# NFL-0038 — Support kicker and team-defense draftable assets

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-22
- Updated: 2026-08-22
- Depends on: NFL-0011, NFL-0014, NFL-0015, NFL-0028

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#supported-matrix)
- [Domain Model](../../domain/domain-model.md#draftableasset)
- [Data and Player Identity](../../data/data-and-identity.md#identity-resolution)
- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)
- [Extension–Backend Protocol](../../contracts/protocol.md#approved-provider-expansion)
- [ADR-0003](../../architecture/decisions/0003-model-team-defenses-as-draftable-assets.md)

## Outcome

The neutral backend can represent, value, and recommend K and DEF draftable assets reproducibly
for the supported 8-team snake redraft, or reject a precisely identified unsupported scoring/data
combination without changing canonical state.

## Context

The approved private Sleeper format includes K and DEF. Current neutral roster, player-reference,
and player-pool constraints only admit QB/RB/WR/TE, so a Sleeper adapter alone cannot initialize
the league safely. K is an individual player; DEF is a team asset and needs different identity and
data semantics.

## In scope

- Generalize the internal domain vocabulary and invariants from player-only to explicit draftable
  assets while preserving existing individual-player behavior.
- Add K and DEF through neutral `LeagueConfig`, roster legality, draft availability, and the
  authoritative FastAPI/OpenAPI contract; regenerate the checked TypeScript consumer.
- Create versioned exact identity/crosswalk rules for kickers and team-defense assets, including
  DEF provider ID, NFL-team, season/validity provenance, conflicts, and no-name-guess behavior.
- Define a versioned semantic codebook for kicking and defense scoring. Reject every unmapped or
  unsupported nonzero provider scoring field visibly.
- Add source-approved prepared data/features, deterministic projections, valuation, replacement,
  ranking explanations, confidence behavior, and position-segment validation for K and DEF.
- Add sanitized fixtures and tests for both positions across identity, configuration, scoring,
  roster assignment, draft/reconciliation, protocol, data publication, recommendations, and
  reproducibility.

## Out of scope

- Sleeper surface detection, API requests, manifest permissions, polling, or live adapter code.
- Changing ESPN behavior or enabling any provider that has not separately met its acceptance
  criteria.
- A name-based DEF mapping, fabricated features, or silently approximated scoring.

## Implementation summary

The neutral implementation now accepts K/DEF roster and player-reference positions, represents DEF
as an explicit team-defense asset, and persists the asset type without breaking prior JSON records.
The authoritative FastAPI/OpenAPI contract and generated extension consumer were regenerated.

The versioned `semantic-v2` scoring codebook accepts explicit K/DEF semantic rules and rejects
unknown rules at the API boundary. Curated data distinguishes a team-defense asset, transforms
approved regular-season `pbp` data into explicit K/DEF weekly fields, produces time-safe K/DEF
features, writes a publishable prepared pool, and validates exact provider mapping/type/season
safeguards. The deterministic projection baseline, replacement/ranking path, and reproducible
promotion evidence have position-specific K/DEF coverage. The Sleeper adapter remains out of scope.

## Acceptance criteria

- [x] Neutral domain/API configuration accepts K and DEF only with explicit roster eligibility and
  produces a regenerated, checked OpenAPI/TypeScript contract.
- [x] K resolves as an individual player and DEF resolves as an exact team-defense asset with
  versioned provenance; ambiguous or stale identities remain unresolved.
- [x] Every supported nonzero K/DEF scoring rule maps through a versioned semantic codebook; an
  unrecognized rule produces a stable unsupported outcome.
- [x] Published prepared data and deterministic models yield explainable, pinned K/DEF values,
  replacement levels, and rankings without leakage or unrecorded fallback.
- [x] Position-specific tests and backtests cover K and DEF and pass the declared reproducibility
  and regression gates.
- [x] Existing QB/RB/WR/TE behavior and the current ESPN contract/fixtures remain compatible.

## Validation

- [x] Run applicable backend format, lint, type, test, build, OpenAPI drift, extension contract,
  documentation, and repository-drift checks.
- [x] Record K/DEF data-source/license, identity-coverage, scoring-codebook, and model-segment
  validation evidence without committing restricted or private payloads.

Current slice evidence (2026-08-22): backend format, lint, mypy, pytest (60 passed), build, and
OpenAPI drift checks passed. Extension format/lint/type-check/test (24 passed) and build passed;
the generated contract accepts K/DEF. Documentation links and fixture sanitization passed. `npm ci`
initially exposed a package-lock inconsistency; npm regenerated the lockfile without changing
declared dependencies, after which clean installation passed. npm reported one high-severity audit
advisory; no dependency update was made in this ticket.

Completion evidence (2026-08-22): backend pytest passed with 63 tests; the extension test suite
passed with 24 tests. The checked OpenAPI generation, backend/extension builds, and documentation
checks passed. A read-only, non-retained validation against the approved 2025 regular-season
nflverse PBP source derived 43 kickers, 32 team defenses, and 1,080 weekly K/DEF rows. The
synthetic fixture validates exact provider mapping/type/season safeguards, atomic publication of a
prepared K/DEF pool, and reproducible K/DEF model-promotion evidence. `git diff --check` passed;
the repository-drift command necessarily reports this intended uncommitted change set, while the
OpenAPI drift check proves generated contract consistency.

## Completion summary

Implemented neutral K/DEF support across domain/configuration, API/OpenAPI, identity, curation,
prepared-pool publication, deterministic projection/value/replacement/ranking, and backtest
coverage. The completed work preserves existing QB/RB/WR/TE behavior and introduces no provider
runtime adapter or private data. Sleeper implementation remains governed by NFL-0037.

## History

- 2026-08-22 — Created in Backlog after the approved Sleeper test-league format exposed K/DEF as
  a neutral domain/model prerequisite.
- 2026-08-22 — Started by Codex after all listed dependencies were confirmed done.
- 2026-08-22 — Implemented the neutral position/asset/API/scoring/projection slice and regenerated
  the contract; source transformation, coverage, and promoted-model evidence remain.
- 2026-08-22 — Completed after PBP source transformation, prepared-pool publication, exact mapping
  safeguards, K/DEF promotion evidence, and all applicable quality checks passed.
