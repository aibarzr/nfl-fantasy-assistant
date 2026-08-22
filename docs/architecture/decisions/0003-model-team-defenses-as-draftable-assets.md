# ADR-0003: Model team defenses as draftable assets

- Status: Accepted
- Date: 2026-08-22
- Supersedes: none

## Context

The supported private Sleeper league includes both K and DEF roster positions and scoring. Kicker
is an individual football player, but a fantasy team defense is a team-level draftable entity. The
existing MVP language and implementation vocabulary assume only individual QB/RB/WR/TE players.
Treating a defense as a player would make identity, source provenance, availability, scoring, and
reproducibility ambiguous.

## Decision

The MVP supports K and DEF. The neutral domain vocabulary is **draftable asset**: an individual
player (including a kicker) or a team-defense asset. A DEF asset has an exact provider external
identity and authoritative NFL-team/season provenance; it is never synthesized from a display name
or a guessed individual-player identity.

`LeagueConfig`, the generated API contract, prepared data, projections, valuation, replacement,
and recommendations must represent these positions explicitly. Flex eligibility remains a
configuration fact. Every nonzero provider kicking or defense scoring rule must translate through a
versioned semantic codebook or cause a visible unsupported configuration outcome.

## Consequences

- The current `Player`-only implementation vocabulary requires a deliberate migration in the
  prerequisite K/DEF ticket before a Sleeper league with these positions can initialize.
- K and DEF need separately covered feature sources, deterministic position/asset models,
  confidence behavior, and position-segment validation.
- Provider identity mappings must distinguish individual-player and team-defense assets and must
  not use numeric-ID equivalence or name guessing.
- Existing ESPN behavior remains unchanged unless and until it supplies supported K/DEF data under
  the same neutral contract.

## Alternatives considered

### Treat a defense as a player

Rejected. It collapses distinct identity and provenance rules, invites name-based guessing, and
cannot faithfully express a team-level projection.

### Reject K and DEF in the Sleeper adapter

Rejected. The approved supported league uses both positions; rejecting them would exclude the
intended MVP configuration.

### Add provider-specific K/DEF handling only in Sleeper

Rejected. Roster legality, scoring, value, availability, and reproducibility belong to neutral
backend/domain layers, not an extension adapter.
