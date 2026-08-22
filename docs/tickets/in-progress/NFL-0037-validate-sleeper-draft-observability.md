# NFL-0037 — Validate Sleeper draft observability and API boundaries

- Status: In Progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-22
- Updated: 2026-08-22
- Depends on: NFL-0003, NFL-0011, NFL-0034

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#supported-matrix)
- [Architecture Overview](../../architecture/overview.md#platform-adapter-strategy)
- [ADR-0002](../../architecture/decisions/0002-extension-bound-provider-api-access.md)
- [Data and Player Identity](../../data/data-and-identity.md#sources-and-compliance)
- [Local Security Threat Model](../../security/threat-model.md#required-controls)

## Outcome

A dated, sanitized finding establishes whether an extension-bound Sleeper adapter can safely
initialize and reconcile the supported 8-team NFL snake redraft using documented read-only API
facts, with exact surface, identity, configuration, player-reference, and recovery evidence.

## Context

Sleeper is an approved second provider, but no runtime behavior or manifest permission is justified
until a private, authorized mock-draft investigation proves the required facts and safe-stop cases.
The existing ESPN implementation and fixtures remain unchanged. K and DEF are approved MVP assets,
but their neutral domain/data/model implementation is tracked separately in NFL-0038.

## In scope

- Read-only inspection of an operator-authenticated Sleeper mock/test draft; never request,
  capture, or retain credentials, cookies, invite URLs, or real league payloads.
- Confirm the exact desktop draft surface and the minimal candidate web/API hosts.
- Record documented API endpoints, response shapes, rate/failure behavior, and the evidence for
  complete initial/recovery snapshots.
- Verify active user ID, roster ID, and draft slot together; verify 8-team snake configuration,
  ordered picks, and every target roster/scoring code required by `LeagueConfig`.
- Identify provider-scoped individual-player and team-defense IDs and validate a proposed versioned
  crosswalk route, including rookies, K/DEF, duplicates, and unresolved cases.
- Produce sanitized fixtures and a narrow finding or ADR update suitable for offline tests.

## Out of scope

- Any Sleeper runtime adapter, manifest permission, polling implementation, K/DEF backend-contract
  or model change, player-data ingestion, browser automation of picks, or use of a real family
  league.
- Approval of Sleeper data as a historical, market, or model input.

## Discovery progress

On 2026-08-22, an operator-authenticated standalone Sleeper mock draft established the candidate
desktop path shape `https://sleeper.com/draft/nfl/<draft-id>`. Its visible pre-draft board showed
eight teams, thirteen rounds, the expected snake reversal, and the supported QB/RB/WR/TE/flex/K/DEF
roster categories.

The documented `GET /v1/draft/<draft-id>` response returned `200` with `type=snake`,
`status=pre_draft`, `sport=nfl`, `season=2026`, eight slot-to-roster entries, and configuration
keys for eight teams, thirteen rounds, roster slots, and CPU autopick. Before any team is claimed,
its `draft_order` is empty and `GET /v1/draft/<draft-id>/picks` is an empty array. The associated
mock `GET /v1/league/<league-id>/users` and `/rosters` endpoints returned `null`; this mock cannot
establish league-backed user/roster evidence in its current state.

After the operator manually claimed the first displayed team, the page visibly associated that
account with draft slot one and showed the corresponding snake turns. A second
`GET /v1/draft/<draft-id>` still returned an empty `draft_order`, although a non-empty opaque
`creators` value was present. Neither creator metadata nor a visible display name is accepted as a
user-ID-to-slot mapping. This pre-draft state therefore remains insufficient for trusted
initialization; a started-draft observation or a league-backed draft must prove the mapping.

Starting the mock redirected the browser to a new opaque draft identity. The original pre-draft
record remained an independent 13-round record, while the new record returned `status=drafting`,
`type=snake`, `sport=nfl`, eight teams, fifteen rounds, one `draft_order` entry for the claimed
account, and eight slot-to-roster entries. The claimed creator ID mapped to draft slot one. An
adapter must treat a changed provider draft ID as a new candidate session and never merge the old
pre-draft state into it.

`GET /v1/draft/<active-draft-id>/picks` returned fifteen contiguous picks. Every pick included
`pick_no`, `round`, `draft_slot`, and a non-empty `player_id`; the returned player IDs were unique
in this sample. Pick metadata contains player display and football attributes, but those remain
corroborating fields rather than identity. The standalone mock supplied no `roster_id` on any pick
and `picked_by` only for the claimed account. Every pick did expose a valid slot from one through
eight, so the adapter may use the observed `draft_slot` as the provider team reference after
documenting its draft scope. It must not require a roster ID for this mock path.

The active mock has no league ID, scoring settings, or roster-position configuration in its draft
response. It cannot validate the required semantic `LeagueConfig` codebook or a league-backed
roster/user mapping; that needs a separate private test league rather than the standalone mock.

An operator-created private test league supplied that missing route. Its draft record is an
8-team, 13-round NFL snake pre-draft with a league ID and eight slot-to-roster entries. Its
`GET /v1/league/<league-id>` response contains `roster_positions`, `scoring_settings`, and league
settings; `GET /users` returned one user and `GET /rosters` returned eight rosters with one owner
that resolves to that user. Combining the owner roster ID with `slot_to_roster_id` derived exactly
one user slot, even while `draft_order` remained empty. This is a safe candidate initialization
route provided every required relationship is present, unique, and scoped to the same league/draft.

The test-league roster positions include `K` and `DEF`, and its scoring settings include defensive
and kicking rules. The user approved K/DEF as supported MVP assets. The current neutral
`LeagueConfig`/OpenAPI roster-slot position set was limited to QB/RB/WR/TE; NFL-0038 has completed
the neutral K/DEF domain/data/model/contract support. This otherwise valid configuration still
needs Sleeper-specific identity and recovery evidence before it can initialize.

No identifier, player, user, league, roster, draft, cookie, credential, or raw payload was
retained. The current evidence establishes a safe candidate league-backed pre-draft initialization
route when all relationships are present, unique, and same-scoped. It remains insufficient for
complete-pick recovery/reconciliation and individual-player/team-defense identity coverage; those
gaps must remain visible unavailable outcomes.

## Acceptance criteria

- [ ] The finding records an exact supported URL rule and rejects nearby/unsupported surfaces.
- [ ] It identifies a documented structured source for draft, user/roster/slot, configuration, and
  ordered picks, or records each unavailable fact without guessing.
- [ ] It establishes whether a complete pick response is authoritative enough for initialization,
  reload, missed-event recovery, and idempotent event construction.
- [ ] It records every consumed field, retention/sanitization rule, terms/rate guidance, and
  private/non-commercial use limitation required to promote the source.
- [ ] It establishes or explicitly rejects a safe Sleeper-player-ID to internal-identity route.
- [ ] The evidence contains no credentials, cookies, invite URLs, real league/user identifiers,
  or raw provider payloads.

## Validation

- [ ] Run the fixture sanitizer/validator introduced by the finding and the applicable extension,
  backend, documentation, and contract checks once implementation exists.
- [ ] Confirm normal CI can execute entirely from sanitized fixtures and has no live Sleeper call.

## Completion summary

Complete when closing the ticket, including the evidence supporting `Resolution: Done`.

## History

- 2026-08-22 — Created after approval of the extension-bound Sleeper API design.
- 2026-08-22 — Started by Codex for read-only mock-draft and API discovery.
- 2026-08-22 — Recorded sanitized pre-draft mock/API findings; user identity and complete-snapshot evidence remain unavailable.
- 2026-08-22 — Claimed-team observation confirms visible slot one, but the pre-draft API still omits draft order; recorded as an identity safe stop.
- 2026-08-22 — Started-draft mock confirms current-draft identity, ordered picks, player IDs, and draft-slot coverage; standalone mock lacks league configuration and roster ownership.
- 2026-08-22 — Private test league confirms configuration, user/roster, and pre-draft slot mapping; K/DEF configuration exposes a current `LeagueConfig` compatibility gap.
- 2026-08-22 — User approved K and DEF support; recorded neutral domain/data/model work as NFL-0038 rather than a Sleeper-only exception.
