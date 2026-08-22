# ESPN draft observability finding — 2026-07-30

## Scope and evidence

This Phase 1 finding is limited to the supported ESPN desktop draft surface and the sanitized
8-team evidence in this directory. The original browser captures remain local-only and are not
needed to run the fixture validation.

## Supported browser activation rule

An operator-confirmed mock-draft URL establishes the exact supported activation rule as
`https://fantasy.espn.com/football/draft`. The extension must require that exact hostname and
pathname; query parameters are not part of the surface rule and must not be retained in fixtures,
logs, diagnostics, or source. In particular, the confirmation's league, team, and member
identifiers were deliberately discarded. Lookalike hosts, other subdomains, and every other path
are unsupported and must not initiate observations.

| Sanitized evidence | What it establishes | Completeness |
|---|---|---|
| `espn-8-team-initial-snapshot.json` | An 8-team `SNAKE` draft, manual scheduled order, roster configuration, scoring configuration, and ESPN player-reference shape | Configuration and scheduled order only; no accepted picks |
| `espn-8-team-selected-picks.json` | Browser-received `SELECTED` WebSocket observations with a team reference and ESPN player external ID | A complete captured sequence of 128 observed messages; not a general recovery snapshot |
| `espn-player-reference-sample.json` | ESPN numeric player IDs, including the negative D/ST form | A small position-coverage sample, not a crosswalk |
| `synthetic-unsupported-team-count-10.json` | The normalized rejection path for a non-8-team configuration | Synthetic validation input, not ESPN observability evidence |

The capture contains 128 scheduled positions and 128 `SELECTED` observations. Their team
sequence agrees position-for-position, and no player reference repeats in this completed capture.
That makes the sequence useful evidence for the *completed captured session*, but it does not
prove a provider-issued event ID or a reusable recovery endpoint.

## Ranked observation mechanisms

| Rank | Mechanism | Suitable facts | Limits and required handling |
|---:|---|---|---|
| 1 | Structured response consumed by the ESPN draft page | Initial `LeagueConfig` input: team count, draft type, scheduled order, roster and scoring configuration; provider player references | The observed response's scheduled picks do not contain accepted player selections. Do not present it as a recovery snapshot. |
| 2 | Browser-received WebSocket `SELECTED` messages | Live team/player pick observations after a complete, contiguous sequence has been established | The source's trailing numeric field has only 16 distinct values across 128 picks, so it is not accepted as overall pick or event ID. No stable provider event ID was observed. |
| 3 | Browser-observable application state | Not established by this evidence | No sanitized state-object capture was retained. It is not an implemented fallback until a future authorized capture proves shape and completeness. |
| 4 | DOM/pick-history rendering | Diagnostic display only | The supplied visual page shows pick history, but no sanitized DOM capture establishes selector stability or completeness. Virtualized lists must never be treated as a complete snapshot. |

## Fact mapping and safe-stop rules

| Required fact | Observed source | Allowed normalization | Safe stop |
|---|---|---|---|
| Initial league configuration and scheduled draft order | Structured page-consumed response | Normalize team references to scoped opaque IDs; retain the one-based scheduled order | Reject any team count other than 8, non-`SNAKE` type, unknown roster/scoring representation, missing order, or order inconsistent with team count. |
| Live pick | Received `SELECTED` WebSocket message | Use the observed team reference plus `{ provider: "espn", external_id }`. Treat the trailing numeric code as opaque. | Do not mutate state when the message is malformed, the player reference is unresolved, or its team cannot match the expected scheduled slot. |
| Overall pick and idempotency key for a contiguous live stream | The position of a received `SELECTED` message checked against the scheduled order | Derive the one-based overall pick only while every predecessor is present and the observed team sequence matches the scheduled order. Build the deterministic event key from the scoped provider draft identity and derived overall pick. | On a gap, duplicate, restart, unknown sequence origin, or schedule mismatch, enter reconciliation/blocked state rather than guessing an ordinal or accepting a second transition. |
| Recovery snapshot after reload or a missed event | No authoritative-enough source observed | None | Preserve accepted canonical state, mark recommendations non-current, and request a future sanitized capture of a complete pick snapshot or a verified replay mechanism. Do not reconstruct accepted history from a partial DOM view or the configuration response. |

The scoped provider draft identity used in an event key remains opaque at the extension boundary. It
is not represented in these fixtures because real account- and league-scoped identifiers are
deliberately removed during sanitization.

## Decision

No architectural boundary changes are needed: the result follows the adapter order already set in
the [architecture overview](../architecture/overview.md#platform-adapter-strategy). A future ESPN
adapter may use the first two observed mechanisms, but it must implement the safe stops above and
cannot claim reload/missed-event recovery until a complete authoritative-enough source is
observed. This is a Phase 1 finding, not permission to automate ESPN actions or to bypass platform
access controls.

`node scripts/check_espn_spike_fixtures.mjs` validates the fixture invariants, including the
captured full-sequence/order agreement and absence of duplicate captured player references.
