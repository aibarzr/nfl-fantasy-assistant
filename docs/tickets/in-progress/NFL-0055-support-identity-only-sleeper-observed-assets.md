# NFL-0055 — Support identity-only Sleeper observed assets

- Status: In Progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0039, NFL-0044, NFL-0045

## Canonical sources

- [ADR-0004](../../architecture/decisions/0004-identity-only-observed-sleeper-assets.md)
- [Architecture Overview — Offline versus live processing](../../architecture/overview.md#offline-versus-live-processing)
- [Data and Player Identity — Prepared and runtime identity](../../data/data-and-identity.md#identity-resolution)
- [Recommendation Engine — Layered model](../../modeling/recommendation-engine.md#layered-model)

## Outcome

A checksum-verified Sleeper runtime resolves an exact, already-drafted identity that lacks
recommendation features, applies its roster/availability effects, and keeps it excluded from
ranking inputs and outputs.

## In scope

- Publish and validate a narrow identity-only artifact in a new immutable crosswalk-derived dataset.
- Load exact observed identities beside, but separately from, prepared recommendation assets.
- Use their canonical positions for drafted-position calculations without recommending them.
- Add documentation, ADR, and synthetic runtime/recommendation tests.

## Out of scope

- Projection fallback, value imputation, name-based identity resolution, or changing an active
  draft's pinned dataset.

## Acceptance criteria

- [ ] An exact unscored identity resolves and is accepted as a pick without becoming a candidate.
- [ ] Prepared recommendation inputs remain complete for—and only for—the prepared pool.
- [ ] Runtime rejects malformed, conflicting, or non-exact observed-identity artifacts.
- [ ] Publication and runtime tests prove deterministic provenance and recommendation exclusion.

## Validation

- [ ] Run applicable backend, extension, documentation, and repository quality checks.
- [ ] Confirm no private provider payload, draft data, or generated artifact is committed.

## Blocker

None.

## Completion summary

Complete when closing the ticket with validated publication and live-safe activation evidence.

## History

- 2026-08-23 — Started after the operator approved the ADR-backed identity-only path needed by the
  full-coverage data publication.
