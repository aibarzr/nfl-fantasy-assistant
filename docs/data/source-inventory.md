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
| Intended inputs | 2022–2025 regular-season play-by-play/player-week/team-week statistics, rosters, player identity attributes, snap counts, and dated depth-chart state. |
| Consumed fields/downstream products | Stable player identifiers/attributes feed the identity crosswalk; player/week usage, opportunity, efficiency, and availability feed semantic features; roster/depth information informs season-state features. For K, play-by-play supplies kicker identity plus field-goal and extra-point attempts/results. For DEF, play-by-play/team-week data supplies exact team, sacks, takeaways, touchdowns, and points/yards allowed. Raw source column names do not cross the data boundary. |
| Credentials/retrieval method | No project credential; use the package's documented public downloader. Cache and raw snapshots remain local under `data/`. |
| Freshness | Historical seasons are immutable enough to refresh only for corrections. Player statistics are normally updated nightly after game days; rosters daily at 07:00 UTC; depth charts daily at 07:00 UTC with timestamped updates from 2025. Fetch status is checked from the [nflverse automation schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html). |
| Coverage/gaps | Player statistics and rosters support the initial period. Do not assume participation or injury coverage: participation after 2023 is post-season only, and the documented injury feed has no 2025 data. Missing source fields remain missing/uncertain; they are never fabricated. |
| License/redistribution | `nflverse-data` is published under [CC BY 4.0](https://github.com/nflverse/nflverse-data/blob/master/LICENSE.md), which requires attribution when shared. The downloader documentation also says underlying NFL data remain governed by their owners' terms. Therefore local retrieval and transformation are approved; committing, redistributing, or publishing a raw/derived artifact additionally requires per-input license/provenance review and required attribution in its manifest. |
| Failure behavior | Retain the last complete validated published version; do not replace it with a partial download. A missing/stale season-state input reduces feature freshness/confidence and blocks publication when a model-critical field fails its declared threshold. |

## Excluded: FantasyPros API/data as a market prior

| Metadata | Decision |
|---|---|
| Owner/endpoint evaluated | FantasyPros API and data, [official terms](https://api.fantasypros.com/public/v2/terms-of-use). |
| Review result | **Not approved.** The terms require provider approval and an API key, limit permitted data use, forbid distributing API materials, and prohibit using the data to compete with FantasyPros. This project has no written permission establishing a compliant use. |
| Credentials/retrieval | No credential, endpoint, scrape, captured response, ranking, ADP, or projection from FantasyPros may be added to source, fixtures, datasets, or runtime requests. The deferred FantasyPros browser surface is not evaluated here. |
| Freshness/failure | No polling or cache is permitted. Its absence is not interpreted as a zero market score. |

## Approved for discovery only: Sleeper read-only live-draft API

| Metadata | Decision |
|---|---|
| Owner and interface | Sleeper, [Sleeper API](https://docs.sleeper.com/), read through an extension service-worker adapter rather than the backend. |
| Permitted scope | Authorized private, non-commercial mock-draft discovery only. This approval does not add a production runtime request or authorize collecting credentials, cookies, invite URLs, or real league payloads. |
| Intended facts | Draft identity/type/order, user-to-roster/slot evidence, league configuration, ordered picks, provider individual-player and team-defense IDs, and API failure/rate-limit behavior. |
| Credentials and retention | The documented API is read-only and does not require an API token. Browser authentication material is never extracted or retained. Sanitized fixtures contain synthetic or redacted identifiers only; raw captures remain local. |
| Identity and data use | Provider individual-player and team-defense IDs feed only the provider-to-internal identity validation path. They are not approved as a historical, market, or projection input. |
| Required promotion evidence | Re-review current terms and rate guidance, exact endpoints/fields, supported draft semantics, complete-snapshot behavior, mapping coverage, polling/backoff policy, and manifest permissions before enabling runtime use. |
| Failure behavior | API unavailability, malformed data, throttling, incomplete snapshots, or unresolved identity leave recommendations non-current; the adapter must not infer state from a partial page. |

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
