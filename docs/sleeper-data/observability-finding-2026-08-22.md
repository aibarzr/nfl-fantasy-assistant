# Sleeper draft observability finding — 2026-08-22

## Scope and activation

This finding is limited to an authorized private 8-team NFL snake test draft. The confirmed desktop
activation rule is `https://sleeper.com/draft/nfl/<draft-id>`, where the opaque draft identifier is
private configuration and must never be retained in fixtures, logs, diagnostics, or source.
Lookalike hosts, other paths, malformed identifiers, and a surface without a validated matching
draft response are unsupported.

## Ranked sources and recovery

| Rank | Source | Established facts | Required safe stop |
|---:|---|---|---|
| 1 | Documented draft, league, user, roster, and picks API responses | Draft type/status, 8-team configuration, user-to-roster-to-slot relationship, semantic league configuration, and current ordered picks | Reject missing, non-unique, cross-scoped, non-8-team, or non-snake facts. |
| 2 | Documented player catalog | Provider player IDs, position, team attributes, and team-defense records | Never elevate names or incomplete crosswalk fields into identity. |
| 3 | Browser board | Exact surface activation, visible state, and diagnostic comparison with an API snapshot | Never infer completeness or identity from the virtualized DOM. |

The observed `GET /v1/draft/<draft-id>/picks` response returned `200` and a complete current array
whose entries were strictly ordered and contiguous by `pick_no`. Each observed entry included a
nonempty `player_id`, `draft_slot`, `round`, `roster_id`, `draft_id`, and position/team metadata.
The response draft identity agreed with the requested draft. A page reload restored the same board
state, and the API snapshot agreed with the visible current picks. The adapter may use this
endpoint as a complete recovery snapshot only after validating every entry against the active
draft identity, expected snake order, declared slot range, and identity resolution outcome.

No event stream has been accepted. Runtime observation initially polls the validated current-picks
snapshot, derives a deterministic idempotency key from scoped provider draft identity plus
`pick_no`, and sends only neutral observations. A non-contiguous sequence, changed accepted pick,
unresolved asset, malformed response, stale snapshot, or API failure blocks freshness and invokes
reconciliation; it never reorders or guesses picks locally.

## Identity and K/DEF

The player catalog uses provider-scoped `player_id` values. Its GSIS and ESPN fields have
incomplete coverage, so neither names nor a field-presence assumption is an automatic
Sleeper-to-nflverse identity route. A released adapter requires a versioned exact mapping table;
unmapped or conflicting individual-player values remain unresolved. K follows the
individual-player route.

`DEF` catalog records are team-defense assets, not players. A released adapter must require an
exact provider team-defense mapping with the active NFL team and season-validity provenance. It
must reject a team-defense reference that has no exact mapping or whose declared position is not
`DEF`.

## API limits and operational controls

Sleeper documents its API as read-only, non-commercial, and token-free. It advises a ceiling of
1,000 calls per minute and says the roughly 5 MB player catalog should be fetched no more than
once per day. The implemented adapter may make an on-demand, service-worker-only recovery read of
the documented draft and picks endpoints after exact-surface activation and local pairing. It does
not poll, cache a pick list, submit a backend mutation, or initialize a live draft. Any future
polling must add bounded backoff for documented `400`, `404`, `429`, `500`, and `503` failures. The
player catalog remains a locally cached, versioned discovery/identity input, not a per-pick call.

This finding authorizes the bounded recovery-validation adapter. Identity prepared-pool coverage
and an end-to-end acceptance fixture remain mandatory before live initialization.
