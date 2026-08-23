# Data and Player Identity

## Responsibilities

The data subsystem converts external datasets into versioned, validated inputs for projection and live runtime. It does not make draft decisions. nflverse/nflreadpy records remain data-layer types and are translated before leaving the layer.

## Sources and compliance

Use nflreadpy and nflverse as the primary historical/feature foundation. FantasyPros consensus information is an external market prior where it is lawfully and appropriately available. Before enabling a source, record:

- Exact dataset/endpoint and owner.
- License or terms governing access, storage, transformation, and redistribution.
- Retrieval method and required credentials.
- Expected update cadence and known coverage gaps.
- Fields actually consumed and downstream products.

Do not commit or redistribute source data without confirmed permission. Respect platform terms and access restrictions; do not design around bypassing authentication or controls.

Live league observations are not model inputs. A provider API used by an extension adapter still
requires a source-inventory record for terms, consumed fields, retention, polling/failure policy,
and identifier handling. It must not be repurposed as historical, market, or player-value data
without a separate approval.

The current Phase 1 approval record, review dates, and exclusions are in the
[source inventory](source-inventory.md). It is required evidence before an ingestion source is
enabled, but does not replace per-version manifest provenance.

## Data lifecycle

```text
source manifest -> raw snapshot -> normalized/curated tables
                -> identity crosswalk -> weekly semantic features
                -> projections/prepared asset values -> published dataset version
```

- **Raw:** immutable source-shaped snapshot plus retrieval metadata; local by default.
- **Curated:** stable typed Parquet tables with normalized keys and documented semantics.
- **Cache:** safely replaceable downloads/computation, never an authoritative version.
- **Published version:** an atomic manifest pinning source snapshots, transforms, schemas, validation results, and output files.

Never publish a partially updated dataset. Build into a staging version, validate, then atomically make it available for new sessions. Active drafts remain pinned to their loaded version.

## Initial coverage and freshness

Start with seasons 2022–2025 and reassess through backtesting. A starting recency prior may be 55%/25%/13%/7% from newest to oldest, plus recent 4-game and 8-game windows; these values are model configuration, not immutable data rules.

Classify inputs:

- **Historical:** prior seasons, play-by-play, career statistics, combine; refresh infrequently.
- **Season state:** rosters, depth charts, snaps, usage; refresh daily or weekly according to source cadence.
- **Fantasy market:** ECR, ADP, rankings, projections; refresh more frequently and retain uncertainty/movement when available.
- **Live league:** picks, rosters, league configuration; observe from the supported platform in real time and persist in application state rather than curated historical data.

Every material observation retains source and `updated_at`; published features also retain source-version lineage.

## Canonical tables

The exact schemas will be versioned with implementation, but the initial semantic outputs are:

- `draftable_assets`: internal identity, asset type, and stable player or team-defense attributes.
- `asset_external_ids`: provider, external ID, internal asset ID, resolution method, provenance, validity/conflict state.
- `sleeper_crosswalk_coverage`: provider/season/position totals plus resolved and blocked counts
  for the catalog and the prepared pool; it is emitted only with a validated Sleeper crosswalk.
- `player_week_features`: one player/season/week with usage, opportunity, efficiency, role, and availability measures.
- `market_rankings`: player, format, rank/ADP, uncertainty/range, source and timestamp.
- `player_projections`: player, league/scoring context class, expected/floor/ceiling/confidence, model and feature versions.
- `prepared_recommendation_inputs`: the selected prepared assets' typed projection/value outputs,
  uncertainty, ranking market prior, warnings, source timestamp, and model/normalization versions.
  It is produced beside `prepared.parquet`; it is not raw source data and is sufficient only to
  recompute state-dependent replacement/VOR and ranking under the pinned model.
- `dataset_manifest`: dataset version, schemas, source timestamps/checksums, transform revision, and validation summary.

Raw columns are not exposed directly to the draft engine. Feature names must express stable football/fantasy meaning rather than a source's column name.

## Identity resolution

Maintain a many-provider-to-one-internal mapping with unique `(provider, external_id)` keys.
Individual-player assets prefer exact provider IDs and authoritative crosswalks, using `gsis_id` as
the preferred NFL anchor when present while retaining the internal ID for rookies and incomplete
coverage. Kicker is an individual-player asset. Team defense is a distinct draftable asset with
an exact provider identity and authoritative NFL-team/season provenance; it must not be fabricated
as a player or mapped by a team display name.

The curated nflverse player identity record retains both its exact `gsis_id` and `espn_id` where
available. A provider crosswalk may use either exact identifier only with matching position and NFL
team corroboration; if multiple supplied identifiers disagree, if one supplied identifier is
unknown, or if either identity is absent, the result remains unresolved or conflict. These fields
are identity evidence, never display-name matching inputs.

Sleeper player IDs and Sleeper team-defense IDs require their own versioned mapping evidence and
coverage checks. A Sleeper ID must never be equated with another provider's numeric ID, and player
name, NFL team, and position remain corroborating attributes rather than a primary identity.

Controlled fallback normalization may handle suffixes, apostrophes, hyphens, abbreviations, team changes, rookies, and duplicate names. It produces candidates, not automatic truth. Auto-resolution requires a single corroborated candidate under versioned rules; otherwise record `unresolved` or `conflict` and preserve the original reference.

Manual overrides must be explicit rows with reason, provenance, timestamp, and supersession history. Never silently rewrite a mapping already used by an accepted draft event. A local review tool may offer a batch only for still-pending, one-to-one candidates generated from exact display name, position, and NFL team evidence and with no supplied GSIS or ESPN value. It must show the count first and require an explicit confirmation; entries with an authoritative identifier, duplicate candidate, conflict, or team-defense evidence remain individual review work.

A completed local Sleeper crosswalk must pin the catalog manifest plus checksums of the curated
player artifact, reviewed queue, and review decisions. It accepts reviewed entries only when they
target the exact queued internal ID and do not contradict an exact catalog mapping or catalog
identity conflict. The resulting report remains local until the explicit publication step creates a
new immutable dataset version: it re-pins `prepared.parquet` to that new version and writes the
resolved `asset_external_ids.parquet` table plus `sleeper_crosswalk_coverage.parquet`. An existing
dataset version is never altered.

Before a Sleeper draft can initialize, the report must also pin and validate the exact typed
`prepared.parquet` output from one immutable published dataset-version directory. Its declared
checksum, row count, and every row's dataset/feature versions must agree with that dataset's
manifest. Every internal asset in that pool must have a Sleeper mapping; an unmapped asset aborts
publication rather than being omitted or guessed.

At runtime, the backend accepts only that crosswalk-published dataset version. It revalidates the
manifest, prepared rows, crosswalk schema, and coverage, then persists exact Sleeper IDs only for
the prepared assets. The runtime record contains the internal asset ID, position, external ID, and
for `DEF` the exact structural team code; it contains neither a provider display name nor a raw
catalog record. A different dataset, feature, or projection-model pin rejects Sleeper initialization
before canonical draft state changes.

When present, the derived crosswalk version also re-pins `prepared_recommendation_inputs.parquet`
to its new immutable dataset version. The runtime validates a one-to-one match with the prepared
pool and reconstructs only the typed projection/value records needed by the approved draft-ranking
model. It never reruns projection or valuation from baseline scores at draft time. A legacy
crosswalk version without this artifact may activate identities, but it reports recommendation
readiness unavailable and cannot publish a recommendation snapshot.

When a verified current Sleeper catalog and a season-state roster source disagree on an individual
player's team, the mapping remains blocked unless a reviewer records an explicit, timestamped team
transition override naming both teams and the reason. This override is unavailable for DEF and
never updates historical observations or silently replaces the conflicting evidence.

For a current-season Sleeper catalog, exact provider NFL team codes may create only structural,
season-valid DEF identities. They carry no fabricated statistics, features, projection, or value:
those remain dependent on the approved PBP preparation path.

## Feature foundation

Initial weekly semantic measures may include snap/target/rush/red-zone share,
routes/participation, expected and actual fantasy points, points over expected, carries, targets,
receptions, air yards, yards, expected touchdowns, EPA, and success rate. Kicker and team-defense
features require separately documented source coverage and semantics before publication; no
QB/RB/WR/TE feature is silently repurposed as a K/DEF proxy.

Derive higher-level versioned features such as usage, opportunity, efficiency, high-value usage, receiving/rushing role, role stability, and availability. Position-specific projection code consumes these stable features.

For K, regular-season nflverse play-by-play is transformed through the authoritative kicker ID
into field-goal/extra-point attempts, made/missed extra-point counts, conversion measures, and
versioned made/missed distance-band counts. For DEF, the transform produces a stable team asset with NFL-team and
season-validity provenance plus sacks, takeaways, defensive touchdowns, safeties, points allowed,
points-allowed band indicators, and pass/rush yards allowed. The transform rejects incomplete
game identity/score evidence, unknown field-goal outcomes or distances, and excludes postseason
rows; source names and raw columns do not cross the curated boundary.

## Quality gates

A dataset cannot be published unless checks cover:

- Schema/types and required columns.
- Key uniqueness and referential integrity.
- Season/week and rate/range validity.
- Duplicate external mappings and unexplained identity loss.
- Expected row-count/coverage changes by source and position.
- Missingness thresholds for model-critical fields.
- No future information leakage in backtest features.
- Deterministic transforms from the same inputs.
- Complete lineage, timestamps, versions, and licenses/terms metadata.

Fixture-sized synthetic/redistributable datasets must exercise the same transformations in CI; large or restricted raw datasets remain local.
