# Phase 1 Source Inventory

- Review date: 2026-08-22
- Scope: historical/season-state inputs and external market priors for the MVP data foundation,
  including approved K/DEF source routes.
- Decision owner: project maintainers must re-review this inventory before enabling a new source or
  changing an approved source's fields, retention, or redistribution behavior.

This is an approval record for source use, not an authorization to commit raw data. Every retrieval
must record its resolved URL, retrieval timestamp, source release/version, checksum, license note,
and consumed columns in the future dataset manifest.

## Approved: nflverse through nflreadpy

| Metadata | Decision |
|---|---|
| Owner | nflverse project, publishing automated releases in [`nflverse-data`](https://github.com/nflverse/nflverse-data). |
| Exact retrieval interface | [`nflreadpy` load functions](https://nflreadpy.nflverse.com/api/load_functions/): `load_pbp`, `load_player_stats`, `load_team_stats`, `load_rosters`, `load_players`, `load_snap_counts`, and `load_depth_charts`. The resolved `nflverse-data` release URL is recorded by the future source manifest rather than hard-coded. |
| Intended inputs | 2022–2025 regular-season play-by-play/player-week/team-week statistics, rosters, player identity attributes, snap counts, and dated depth-chart state. A current 2026 player/roster snapshot is also approved strictly as season-state evidence for candidate eligibility, current NFL team, and identity reconciliation; it is not treated as historical production or substituted for unavailable 2026 game statistics. |
| Consumed fields/downstream products | Stable player identifiers/attributes, including `gsis_id` and `espn_id` where present, feed the identity crosswalk; player/week usage, opportunity, efficiency, and availability feed semantic features; roster/depth information informs season-state features. For K, play-by-play supplies kicker identity plus field-goal and extra-point attempts/results. For DEF, play-by-play/team-week data supplies exact team, sacks, takeaways, touchdowns, and points/yards allowed. Raw source column names do not cross the data boundary. |
| Credentials/retrieval method | No project credential; use the package's documented public downloader. Cache and raw snapshots remain local under `data/`. |
| Freshness | Historical seasons are immutable enough to refresh only for corrections. Player statistics are normally updated nightly after game days; rosters daily at 07:00 UTC; depth charts daily at 07:00 UTC with timestamped updates from 2025. Fetch status is checked from the [nflverse automation schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html). |
| Coverage/gaps | Player statistics and rosters support the initial period. Do not assume participation or injury coverage: participation after 2023 is post-season only, and the documented injury feed has no 2025 data. Missing source fields remain missing/uncertain; they are never fabricated. |
| License/redistribution | `nflverse-data` is published under [CC BY 4.0](https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md), which requires attribution when shared. The downloader documentation also says underlying NFL data remain governed by their owners' terms. Therefore local retrieval and transformation are approved; committing, redistributing, or publishing a raw/derived artifact additionally requires per-input license/provenance review and required attribution in its manifest. |
| Failure behavior | Retain the last complete validated published version; do not replace it with a partial download. A missing/stale season-state input reduces feature freshness/confidence and blocks publication when a model-critical field fails its declared threshold. Before the 2026 regular season has produced eligible historical observations, a current roster snapshot alone cannot fill missing scoring, K, or DEF feature evidence. |

## Excluded: FantasyPros API/data as a market prior

| Metadata | Decision |
|---|---|
| Owner/endpoint evaluated | FantasyPros API and data, [official terms](https://api.fantasypros.com/public/v2/terms-of-use). |
| Review result | **Not approved.** The terms require provider approval and an API key, limit permitted data use, forbid distributing API materials, and prohibit using the data to compete with FantasyPros. This project has no written permission establishing a compliant use. |
| Credentials/retrieval | No credential, endpoint, scrape, captured response, ranking, ADP, or projection from FantasyPros may be added to source, fixtures, datasets, or runtime requests. The deferred FantasyPros browser surface is not evaluated here. |
| Freshness/failure | No polling or cache is permitted. Its absence is not interpreted as a zero market score. |

## Approved for bounded recovery validation and local identity mapping: Sleeper read-only API

| Metadata | Decision |
|---|---|
| Owner and interface | Sleeper, [Sleeper API](https://docs.sleeper.com/), read through an extension service-worker adapter rather than the backend. |
| Permitted scope | Authorized private, non-commercial mock-draft discovery; service-worker-only recovery validation on the exact supported draft surface; the local once-daily player-catalog snapshot required to build a versioned identity crosswalk; and a verified service-worker initialization handoff. During one active supported draft page, recovery may poll only the documented draft and picks endpoints at a five-second base interval (24 provider calls/minute), with exponential failure backoff capped at sixty seconds. Initialization reads only documented draft, league, roster, user, and picks endpoints, converts validated facts to neutral in-memory requests, and submits them only to the paired loopback backend after its prepared-data and identity runtime reports ready. It does not authorize collecting credentials, browser-authentication material, invite URLs, or real league payloads. |
| Intended facts | Draft identity/type/order, user-to-roster/slot evidence, league configuration, ordered picks, provider individual-player and team-defense IDs, API failure/rate-limit behavior, exact catalog fields needed for provider-to-internal identity mapping, and current recommendation-candidate display labels. Display labels are reduced in the service worker to the exact requested IDs, used only to render the local panel, and never sent to the backend or persisted. |
| Credentials and retention | The documented API is read-only and does not require an API token. Browser authentication material is never extracted or retained. The public player-catalog response is a local raw source snapshot with a manifest/checksum and is never committed; sanitized fixtures contain synthetic or redacted identifiers only. A service worker may make the same catalog read for current recommendation labels, with a 16 MiB response limit, then immediately reduce it to the requested labels in memory. |
| Identity and data use | Provider individual-player and team-defense IDs feed only the provider-to-internal identity validation path. They are not approved as a historical, market, or projection input. |
| Required promotion evidence | Current terms/rate guidance; exact endpoints/fields; supported draft semantics; complete-snapshot behavior; mapping coverage; adapter host/manifest permissions; locally pinned data/model versions; and a ready runtime dataset and identity mapping. Recommendation-runtime activation and bounded polling/backoff are separate implementation/promotion evidence; end-to-end live-draft acceptance remains outstanding. |
| Failure behavior | API unavailability, malformed data, throttling, incomplete snapshots, missing configured identity, non-ready local runtime, or unresolved identity leave recommendations non-current; the adapter must not infer state from a partial page or submit a backend mutation. |

## Approved for bounded external-identity candidate discovery: Wikidata

| Metadata | Decision |
|---|---|
| Owner and interface | Wikimedia Foundation / Wikidata, using the documented read-only MediaWiki Action API or entity endpoint with a descriptive User-Agent and rate-limit/backoff compliance. |
| Permitted scope | A locally initiated, small query for an already-unresolved Sleeper individual-player reference. Its catalog display name, position, and team may locate a candidate, but they only create a review candidate. The accepted evidence must include a Wikidata entity ID and at least one defined stable identifier: ESPN.com NFL player ID (P3686), NFL.com player ID (P9338), or its former numeric scheme (P3539). |
| Excluded scope | Automatic mapping; runtime requests; historical, roster, projection, market, or valuation inputs; bulk catalog enrichment; writing to Wikidata; retaining raw responses or display names in committed artifacts. |
| Credentials/retrieval | No credential. Query only from the offline local-review command, send a descriptive User-Agent, request one candidate at a time, and stop/retry later on a rate-limit response. |
| Freshness and retention | Retrieve at approval time only. Store a local immutable review/decision record with source endpoint, entity revision when available, retrieval time, checksums, and the minimal identifiers needed for the approval; do not commit it. |
| License/redistribution | Wikidata structured data is CC0. This permits the narrow local artifact, but source attribution and review provenance remain in the local dataset manifest. |
| Failure behavior | Missing/ambiguous candidate, identifier absence, HTTP failure, or no explicit operator decision leaves the Sleeper reference unresolved and recommendations non-current. |

## Market-prior fallback

Until a source has written permission and complete provenance/compliance metadata, the permitted
fallback is the versioned own-model player value only. The future valuation layer must omit and
renormalize the market component, set an explicit `market_prior_status=unavailable`, attach the
configured confidence penalty/freshness warning, and preserve that status in recommendation
provenance. It must not replace an unavailable market rank, ADP, dispersion, or movement with
zero. This follows the [player-value fallback requirement](../modeling/recommendation-engine.md#player-value).

## Future source admission checklist

Before admitting any additional historical, season-state, or market source, record its owner,
exact endpoint/dataset/version, terms evidence and review date, credentials, cadence, coverage
gaps, consumed fields, retention/redistribution conditions, failure behavior, and attribution.
If permission or redistribution terms remain uncertain, the source is excluded from committed and
published artifacts.
