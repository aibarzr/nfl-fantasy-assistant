# NFL-0007 — Validate ESPN player identifiers and authoritative crosswalks

- Status: Done
- Resolution: Done
- Phase: 1 — Technical spikes
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0005

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#identity-resolution)
- [Domain Model](../../domain/domain-model.md#identity-resolution)

## Outcome

A reproducible finding identifies stable ESPN player references and credible mappings to internal and GSIS-backed identities, including known gaps and conflicts.

## Scope

Sample veterans, rookies, free agents, duplicate names, team changes, and common formatting differences. Names may generate candidates but may not serve as primary identity.

## Acceptance criteria

- [x] ESPN identifier location, stability, coverage, and namespace are documented with sanitized evidence.
- [x] Available authoritative crosswalks and their provenance are evaluated.
- [x] Unresolved and conflicting examples remain unresolved rather than guessed.
- [x] The finding defines inputs needed by the versioned resolution pipeline without leaking source-shaped records into domain boundaries.

## Validation

- [x] Reviewed sanitized evidence; it contains no personal or league-specific data.
- [x] Confirmed that every accepted route uses a provider external ID, never a player name alone.

## Completion summary

[`ESPN player identity finding — 2026-07-30`](../../espn-data/player-identity-finding-2026-07-30.md)
establishes exact provider-scoped ESPN numeric references and validates nflverse's versioned
ESPN-to-GSIS route. A read-only current-table comparison covered 120 of the 128 captured player
references; the eight negative D/ST references remain explicitly unresolved until a separate
provider-asset mapping is validated. No external player row or identifier was added to the repo.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex after NFL-0005 completed.
- 2026-07-30 — Completed by Codex with explicit quarantine rules for unresolved references.
