# NFL-0021 — Derive availability and rosters from accepted picks

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0019

## Canonical sources

- [Domain Model](../../domain/domain-model.md#draftpick)
- [MVP Specification](../../product/mvp-spec.md#functional-requirements)

## Outcome

Canonical availability and team rosters are deterministic projections of the prepared player pool, accepted picks, configured order, and league roster rules.

## Scope

Implement pure derivation and legal slot assignment/reassignment. Browser rosters and visible/virtualized player lists are observations, never authoritative inputs.

## Acceptance criteria

- [x] Every accepted player is absent from availability exactly once.
- [x] Unresolved observations do not remove guessed players.
- [x] Roster membership follows accepted picks; slot assignment respects flex and legal constraints and can be recalculated.
- [x] Duplicate or contradictory picks fail without corrupting the previous derivation.

## Validation

- [x] Domain/service tests cover the canonical MVP 8-team snake order, flex/bench legality,
  duplicate players, unresolved picks, and reconciliation rebuilds. (10/12-team expansion is not
  in the canonical MVP supported matrix.)
- [x] Pure derivations are deterministic from identical accepted picks and prepared-pool IDs.

## Completion summary

Implemented pure availability subtraction and legal deterministic roster reassignment from
canonical picks; no browser roster/list is used as authoritative state.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
