# ADR-0005: Wikidata external-identity candidates

- Status: Accepted
- Date: 2026-08-23
- Supersedes: none

## Context

An exact current Sleeper reference can be absent from the approved nflverse identity artifact.
It cannot be resolved by display name or assigned a projection. The recovery path needs a locally
retained, licensable source that can supply an independently stable identity candidate for explicit
human review.

## Decision

Wikidata's public CC0 structured data is approved only for local, bounded discovery of an
individual-player identity candidate. The discovery query may use a current Sleeper catalog display
name, position, and team to propose a candidate; none of those fields are sufficient to accept a
mapping. A candidate must carry a Wikidata entity ID and at least one stable NFL-facing identifier
(ESPN NFL or NFL.com), and an operator must explicitly approve the exact queued candidate with
reviewer, timestamp, and reason.

An approved result creates a narrow identity-only asset under ADR-0004. It may resolve an already
observed Sleeper pick and contribute only its position to roster state. It has no historical
features, projection, value, or recommendation input. Raw responses, search strings, candidate
display names, and the local approval artifact remain outside version control.

## Consequences

- The project can recover an exact active-draft observation absent from nflverse without inventing
  an identity or score.
- A source outage, ambiguous search, missing external identifier, or absent operator approval
  leaves the reference unresolved and recommendations non-current.
- Wikidata is not a historical, roster, market, or valuation source, and no runtime network call
  is introduced.

## Alternatives considered

### Treat a name/team/position match as a mapping

Rejected. These are corroborating attributes only and remain insufficient without an explicit
review decision backed by a stable external identifier.

### Use ESPN's undocumented web endpoints

Rejected. ESPN's documented feed access is permission/key-based; the project has no approved feed
agreement.
