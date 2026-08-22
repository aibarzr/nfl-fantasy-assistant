# NFL-0013 — Implement league scoring and prepared baseline player pool

- Status: Done
- Resolution: Done
- Phase: 2 — Data foundation
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0011, NFL-0012

## Canonical sources

- [Domain Model](../../domain/domain-model.md#scoring-and-draft-calculations)
- [Roadmap](../../roadmap.md#delivery-phases)

## Outcome

Prepared data can calculate explicit league scoring and publish a roughly 250–350-player baseline pool with stable internal identities and provenance.

## Scope

Implement scoring from `LeagueConfig.scoring_rules`, supported position handling, identity joins, and a deterministic baseline ordering suitable as input to later projection and valuation tickets.

## Acceptance criteria

- [x] Scoring derives solely from explicit league rules and rejects unsupported semantics visibly.
- [x] The prepared pool contains unique internal players, supported positions, source updates, and feature/dataset versions.
- [x] League size and roster configuration are inputs rather than universal positional constants.
- [x] Missing or unresolved identity is visible and never repaired by name-only guessing.

## Validation

- [x] Tests cover QB passing, RB rushing/reception, WR/TE reception and receiving scoring, plus a
  flex-eligible league context.
- [x] Tests cover unresolved and duplicate-safe identities, deterministic descending-score/tie-ID
  ordering, provenance, and a 350-candidate fixture producing the default top-300 pool.

## Completion summary

Added explicit supported-stat scoring and deterministic prepared-pool selection. `LeaguePreparationContext`
requires team count, roster slots, and flex eligibility; each prepared player carries stable identity,
position, source freshness, and feature/dataset versions.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex; validation evidence recorded above.
