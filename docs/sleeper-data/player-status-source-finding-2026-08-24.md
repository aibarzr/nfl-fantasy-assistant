# Sleeper current player-status source finding — 2026-08-24

## Decision

Approve a narrow, read-only Sleeper player-status feed for current recommendation-risk evidence.
It supplements historical durability; it does not supply medical prognosis, historical injury
labels, market rankings, projections, or identity fallbacks.

## Evidence and scope

The documented endpoint is `GET https://api.sleeper.app/v1/players/nfl`, optionally filtered by
position and `active=true`. Sleeper documents the catalog as a roughly 5 MiB response intended for
at most one refresh each day; the sample player record includes `player_id`, `status`,
`injury_status`, `injury_start_date`, and `practice_participation`.

On 2026-08-24, an authorized read-only query limited to active QBs returned 355 records. All
records contained those five fields. Observed values were:

| Field | Observed values (sanitized aggregate) |
|---|---|
| `status` | `Active`, `Inactive`, `Injured Reserve` |
| `injury_status` | null, `IR`, `NA`, `Questionable` |
| `practice_participation` | null |

This is schema/enum evidence only. No raw catalog, player names, player IDs, private league data,
or request payload was retained in this repository. The observed set is not an exhaustive enum;
unknown provider values reject rather than silently map.

## Translation and identity

The extension may reduce a catalog record to its exact Sleeper `player_id`, neutral status class,
observed-at timestamp, and source revision/checksum. It may retain only the fields needed for the
neutral classification: `status`, `injury_status`, `injury_start_date`, and
`practice_participation`. The backend accepts the result only for an exact reviewed Sleeper mapping;
display names, team, and position are corroboration or presentation facts, never an identity
fallback.

The proposed neutral classes are `healthy`, `limited`, `questionable`, `doubtful`, `out`,
`reserve`, `inactive`, and `unknown`. They describe the provider observation, not a diagnosis or
return-to-play prediction. Conflicting or unmapped provider fields remain `unknown` with a warning.

## Freshness, retention, and failure

Refresh at most once per calendar day, consistent with Sleeper's documentation. The adapter
requires an RFC 3339 observation timestamp and content checksum. It sends no raw catalog or names
to the backend. The backend persists only complete, validated neutral revisions needed for replay;
the raw response is local, replaceable source material and is never committed.

Missing, stale (older than 36 hours), malformed, partial, or conflicting data stays `unknown` and
must not be presented as healthy. The last valid complete overlay remains replayable, but a new
recommendation displays its stale/unknown warning according to the versioned risk policy. No
authenticated or undocumented endpoint, news text, or medical note is authorized.

## Terms and re-review

The documented Sleeper API is read-only and free for non-commercial use; commercial use requires
separate licensing. This local, non-commercial project retains its existing extension-bound
access constraint and does not redistribute catalog content. Re-review this decision before
commercial use, any increase above once-daily catalog retrieval, use of new fields, or a change in
Sleeper terms/API semantics.

## Sources

- [Sleeper API documentation — Players](https://docs.sleeper.com/#players)
- [Sleeper API documentation — Introduction](https://docs.sleeper.com/)
