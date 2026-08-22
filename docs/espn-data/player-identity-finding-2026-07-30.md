# ESPN player identity finding — 2026-07-30

## Result

The ESPN draft evidence supplies a provider-scoped numeric external ID for player observations.
The approved nflverse players release provides a credible ESPN-to-GSIS crosswalk for ordinary
player references, but it does not cover the observed negative defense/team references. Those
references remain unresolved until a separate, versioned defense identity mapping is validated.

## Evidence and coverage

| Evidence | Finding |
|---|---|
| `espn-8-team-selected-picks.json` | 128 unique observed ESPN player references across a complete captured pick sequence. |
| `espn-player-reference-sample.json` | Numeric ESPN reference form occurs across six position codes, including a negative D/ST reference. Position and professional-team codes are corroborating attributes, not identity. |
| [nflverse players release](https://github.com/nflverse/nflverse-data/releases/tag/players) | Its published player table exposes both `espn_id` and `gsis_id`; the [nflverse players build](https://github.com/nflverse/nflverse-players) states that its ESPN IDs are joinable through `gsis_id`. |

On 2026-07-30, a read-only comparison of the 128 sanitized observed pick references with the
current public nflverse players table found 120 exact `espn_id` matches. The eight unmatched
references were exactly the eight negative references in the capture. No player rows or
identifiers from that comparison are committed.

## Resolution policy

1. Preserve the adapter observation as `{ provider: "espn", external_id }`; external IDs are
   strings because valid ESPN references can be negative.
2. Resolve only an exact, unique `espn_id` mapping in a versioned nflverse players input. Store the
   resulting generated internal ID and `gsis_id` when present, together with source version and
   resolution method.
3. If the exact key is absent, duplicated, or disagrees with a prior accepted mapping, record
   `unresolved` or `conflict`. Do not use a display name, team, position, or a numeric-code
   similarity as a substitute.
4. Treat the negative D/ST form as a separate provider-asset class. It has no demonstrated
   player-to-GSIS crosswalk in this evidence, so it remains unresolved rather than being attached
   to a guessed player or team. A future mapping needs its own provenance, version, and uniqueness
   checks.

The identifier is provider-namespaced, not globally numeric: `espn:123` and another provider's
`123` can never share an identity merely by numeric coincidence. The identity pipeline, rather
than an extension adapter, owns crosswalk lookup, conflicts, manual overrides, and provenance.

## Inputs required by the future resolution pipeline

The pipeline needs a versioned nflverse players release, an exact ESPN-ID index, its GSIS/internal
identity output, resolution timestamp, source checksum/version, and a quarantine table for
unresolved/conflicting observations. It consumes neutral provider references and emits internal
domain identities; neither ESPN player records nor nflverse source rows cross into the draft
domain.

This finding establishes a credible mapping route for ordinary player IDs, not a guarantee of
crosswalk completeness across future seasons, rookies, free agents, or D/ST assets. Each published
data version must run coverage, uniqueness, and unresolved-count checks before it can be used in a
draft.
