# NFL-0037 — Validate Sleeper draft observability and API boundaries

- Status: Done
- Resolution: Done
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
- [Sleeper observability finding](../../sleeper-data/observability-finding-2026-08-22.md)

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

After this league was started, the visible draft board transitioned to `drafting`, showed five
ordered selections, and paused at an unclaimed CPU slot. A controlled page reload restored the
same 8-team/13-round board, the visible selections, and the active clock. This is useful UI
continuity evidence, but it does not prove that the documented picks endpoint is a complete,
authoritative recovery snapshot; that endpoint must be inspected directly and compared with the
board before an adapter can rely on it.

The documented `GET /v1/players/nfl` catalog describes player IDs used by draft picks and includes
both individual-player records and 32 `DEF` records keyed by NFL-team code. A live, non-retained
shape check showed that individual-player GSIS and ESPN crosswalk fields are incomplete, including
for kicker records. Therefore the catalog is not an automatic authoritative mapping route to the
internal nflverse identity set. A Sleeper adapter must retain exact provider-ID mappings in a
versioned crosswalk, use a corroborated authoritative identifier only where coverage exists, and
leave unmatched/ambiguous individual players unresolved. `DEF` requires an exact provider
team-code-to-season-valid team-defense mapping and never a name fallback.

Sleeper's documentation describes the API as read-only and free for non-commercial use, requires
no API token, advises staying below 1,000 calls per minute, and limits the full player catalog to
roughly once per day because of its size. The documented failure set includes `400`, `404`, `429`,
`500`, and `503`; runtime use must apply the approved bounded polling/backoff behavior and mark
recommendations non-current rather than infer a missing observation.

No identifier, player, user, league, roster, draft, cookie, credential, or raw payload was
retained. The current evidence establishes a safe candidate league-backed pre-draft initialization
route when all relationships are present, unique, and same-scoped. The documented picks response
was then checked against the active board: it returned `200`, six ordered, contiguous current
picks with a stable provider player reference, draft slot, round, roster reference, matching draft
identity, and metadata position for every entry. A reload restored the same board state before the
comparison. Subsequent controlled test selections visibly covered `K` and `DEF`; the exact
provider mapping gate for those assets is documented in the sanitized finding rather than copied
from the private draft.

## Acceptance criteria

- [x] The finding records an exact supported URL rule and rejects nearby/unsupported surfaces.
- [x] It identifies a documented structured source for draft, user/roster/slot, configuration, and
  ordered picks, or records each unavailable fact without guessing.
- [x] It establishes whether a complete pick response is authoritative enough for initialization,
  reload, missed-event recovery, and idempotent event construction.
- [x] It records every consumed field, retention/sanitization rule, terms/rate guidance, and
  private/non-commercial use limitation required to promote the source.
- [x] It explicitly rejects an automatic Sleeper-player-ID-to-internal-identity route and requires
  a versioned exact mapping table; unresolved values remain a visible safe stop.
- [x] The evidence contains no credentials, cookies, invite URLs, real league/user identifiers,
  or raw provider payloads.

## Validation

- [x] Run `./scripts/quality.sh docs`: Markdown links, existing ESPN fixture sanitization, and the
  new Sleeper fixture validator all pass.
- [x] Confirm the validator reads only committed synthetic fixture files and makes no live Sleeper
  call. Extension/backend/contract checks remain the responsibility of the future adapter ticket.

## Completion summary

The approved extension-bound API design has now been backed by a sanitized, offline-testable
finding. The next ticket may implement a Sleeper adapter only if it also builds the versioned
individual-player and team-defense mapping route described here. This discovery result does not
enable name matching, raw payload retention, a backend-to-Sleeper connection, or a runtime host
permission by itself.

## History

- 2026-08-22 — Created after approval of the extension-bound Sleeper API design.
- 2026-08-22 — Started by Codex for read-only mock-draft and API discovery.
- 2026-08-22 — Recorded sanitized pre-draft mock/API findings; user identity and complete-snapshot evidence remain unavailable.
- 2026-08-22 — Claimed-team observation confirms visible slot one, but the pre-draft API still omits draft order; recorded as an identity safe stop.
- 2026-08-22 — Started-draft mock confirms current-draft identity, ordered picks, player IDs, and draft-slot coverage; standalone mock lacks league configuration and roster ownership.
- 2026-08-22 — Private test league confirms configuration, user/roster, and pre-draft slot mapping; K/DEF configuration exposes a current `LeagueConfig` compatibility gap.
- 2026-08-22 — User approved K and DEF support; recorded neutral domain/data/model work as NFL-0038 rather than a Sleeper-only exception.
- 2026-08-22 — Started the private test draft: the board restored visible ordered picks and active-clock state after reload, but an unclaimed CPU slot prevented further UI-only controlled picks. The public player catalog and documented rate/failure limits reject name-based or automatic Sleeper-to-nflverse identity mapping; exact, versioned mapping evidence remains required.
- 2026-08-22 — Directly compared the documented current-picks response with the reloaded active board; it returned a contiguous, ordered, draft-scoped snapshot. Controlled private test picks visibly covered K and DEF. Added only synthetic derived fixtures, a local validator, and the dated finding; all documentation checks passed.
