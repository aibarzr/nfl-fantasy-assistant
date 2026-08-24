# Offline Data Contract

Phase 2 implements local-only offline preparation. `nflreadpy` is the outer retrieval adapter;
its Polars/nflverse records are serialized as immutable raw Parquet snapshots and never cross into
the domain or future live draft engine.

## Source snapshots

An approved input is identified by the SHA-256 of source, season, dataset, resolved source
version/URL, payload checksum, schema, license note, and consumed columns. The raw payload is
written before its manifest. A failed retrieval or partial write therefore has no manifest and is
not a complete snapshot. Caches are replaceable; `data/raw/` and `data/prepared/` are ignored by
version control.

## Curated tables

Schema version `4` has these keys:

- `players`: `source_player_id`; exact `gsis_id` and `espn_id` where available, normalized
  position/team attributes, source update timestamp, and source-manifest lineage. Both external
  identifiers are nullable because incomplete coverage and rookies require an internal identity
  later; neither is inferred from a name.
- `player_week_features` (curated weekly input): `(source_player_id, season, week)`; count fields
  are events, yard fields are yards, `snap_share` is `[0, 1]`, and null means the source did not
  provide a value (not an observed zero). K rows retain made/missed extra-point counts and
  made/missed field-goal counts by the
  neutral 0–19, 20–29, 30–39, 40–49, and 50+ yard bands. DEF rows retain mutually exclusive
  points-allowed band indicators for 0, 1–6, 7–13, 14–20, 21–27, 28–34, and 35+ points, alongside
  the numeric points allowed and defensive event counts. The complete PBP transform writes an
  observed zero for every unused K/DEF band in a represented player-week; an unavailable source
  value stays null and cannot be silently used as zero by a banded projection. `active` is nullable:
  it is an observed participation/availability fact only when an admitted source establishes it;
  player statistics alone leave it null.

The written table contract records exact Arrow field types. Curated output is deterministic for
the same rows and transform revision; invalid keys, seasons/weeks, ranges, positions, and source
required fields fail visibly.

## Identity and features

Exact provider IDs and authoritative GSIS/ESPN crosswalks are preferred. Normalized names only create
candidates and resolve only when one candidate is corroborated by both team and position under
identity rule version `1`. Unresolved/conflicting evidence remains a result, never a guessed
mapping. Manual overrides retain reason, provenance, UTC timestamp, and a superseded override ID.
A Sleeper crosswalk validation records checksums for its local curated-player artifact, review
queue, and review decisions alongside the catalog source-manifest ID; an accepted review cannot
contradict an exact catalog mapping or a catalog conflict.

Feature version `4` produces a row with an observation cutoff before its target player-week. Its
four-game windows only use earlier rows (including prior seasons), and unavailable history stays
null. Availability is computed only from non-null observed availability facts. A projection omits
unknown availability from its weighted score, emits `availability_unknown`, and applies its
versioned confidence reduction; it never substitutes a neutral healthy score. Historical fantasy
production is represented once as the named historical-production feature rather than duplicated
as another final-score input.

Historical durability uses a separate exact player/team/week eligibility calendar, not the sparse
stat-row sequence. The calendar has `participated`, `did_not_participate`, `unknown`, and `bye`
states with source-manifest lineage. Byes are excluded from rates. Four-game, eight-game,
prior-season, and multi-season rates are available only when every eligible week required by that
window has supported evidence; unknown data never shortens a window or becomes an injury label.

Baseline scoring multiplies only explicit supported league scoring-rule fields. Flat and
distance-band field-goal rules, and linear and banded points-allowed rules, are distinct neutral
semantics; a configuration cannot silently substitute one for another. Pool preparation receives
team count, roster slots, and flex eligibility as a `LeaguePreparationContext`; it has no universal
positional replacement or roster constants. Given enough eligible resolved candidates, the default
deterministic score/tie-break ordering yields the top 300 players.

## Publication and pinning

Dataset manifests record source manifest IDs, transform/schema/feature versions, output checksums
and row counts, every required quality check, timestamps, and license notes. A build stages under
`data/prepared/.staging`, validates, atomically renames into `versions/`, then atomically changes
the active-version pointer. Failures preserve the last active version. A `PinnedDataset` rejects a
different dataset or feature version, so future draft sessions cannot switch silently.

The live backend activates an explicitly selected dataset-version directory rather than a loose
Parquet path or the mutable active pointer. It verifies the whole manifest, typed `prepared.parquet`,
typed Sleeper `asset_external_ids.parquet`, and prepared-pool coverage before persisting only the
exact resolved Sleeper identities for prepared assets. Raw records, display names, and mappings
outside that pool do not enter runtime state. A Sleeper draft must pin that dataset/feature version
and the current projection-model version before initialization.
