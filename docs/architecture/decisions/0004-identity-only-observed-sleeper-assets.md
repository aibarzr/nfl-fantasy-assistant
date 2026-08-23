# ADR-0004: Identity-only observed Sleeper assets

- Status: Accepted
- Date: 2026-08-23
- Supersedes: none

## Context

The recommendation runtime intentionally contains only assets with immutable prepared features,
projections, and values. Live validation showed that a legitimate already-drafted Sleeper asset can
fall outside that set because it has no approved historical feature record. Leaving that identity
unresolved blocks the entire draft; inventing a projection or adding it to recommendations would
violate the data and modeling boundaries.

## Decision

Each new crosswalk-derived Sleeper dataset may publish a separate, checksum-verified
`sleeper_observed_identities` artifact. It contains only exact resolved provider ID, internal asset
ID, position, asset type, and structural NFL team where required—never display names, raw catalog
records, or valuation inputs. Runtime loads these identities into canonical draft resolution in
addition to prepared recommendation assets.

An identity-only asset may be accepted as an observed pick, used in roster and positional-demand
derivation, and excluded from availability because it is not in the recommendation candidate set.
It has no projection, value, confidence, or recommendation input and can never be recommended.
Prepared recommendation inputs remain a complete one-to-one set for the prepared pool.

## Consequences

- A valid live pick outside the scored pool no longer creates an unresolved identity solely for
  missing feature evidence.
- A derived dataset must validate exact one-to-one observed identities and consistency with its
  prepared mappings before runtime activation.
- Recommendation logic must obtain drafted positions from canonical identities when an accepted
  pick is identity-only, while ranking only prepared recommendation inputs.
- Previously published datasets remain valid but lack this optional recovery capability; no active
  draft changes datasets silently.

## Alternatives considered

### Fabricate a zero or fallback projection

Rejected. Missing historical evidence is not a legitimate valuation input and would create an
unreproducible, misleading recommendation candidate.

### Require every catalog asset to have recommendation features

Rejected. It would block legitimate rookies or sparse historical records and makes live recovery
depend on data unavailable at draft time.

### Persist every raw Sleeper catalog record at runtime

Rejected. It expands the runtime trust boundary and retains unnecessary provider data. The narrow
exact-ID artifact is sufficient for canonical observation handling.
