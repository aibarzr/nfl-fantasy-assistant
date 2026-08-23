# NFL-0039 — Build Sleeper identity crosswalk

- Status: Blocked
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-22
- Updated: 2026-08-23
- Depends on: NFL-0011, NFL-0037, NFL-0038, NFL-0041

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#identity-resolution)
- [Source Inventory](../../data/source-inventory.md#approved-for-discovery-and-local-identity-mapping-sleeper-read-only-api)
- [Domain Model](../../domain/domain-model.md#identity-resolution)
- [Sleeper observability finding](../../sleeper-data/observability-finding-2026-08-22.md#identity-and-kdef)
- [Development Guide](../../engineering/development.md#quality-gates)

## Outcome

A versioned, reproducible Sleeper-to-internal draftable-asset crosswalk resolves only exact,
corroborated individual-player and team-defense references for the supported pool, and returns
explicit unresolved/conflict outcomes for every other reference.

## Context

NFL-0037 proved the provider ID namespace and explicitly rejected name-only or incomplete
catalog-field matching. NFL-0038 supplies neutral K/DEF assets and exact team-defense resolution
rules. This ticket provides the data-layer identity evidence required before an extension adapter
can initialize a Sleeper draft.

## In scope

- Define the versioned Sleeper catalog retrieval/cache input and its source-manifest provenance.
- Translate only needed catalog fields into internal data-layer records.
- Resolve individual players through exact, corroborated identifiers and explicit manual overrides
  where required; do not treat display names as primary identity.
- Map K as individual-player assets and DEF through exact provider-team/NFL-team/season-validity
  evidence.
- Produce coverage/conflict/unresolved reports for the published prepared pool, including rookies,
  duplicate names, missing crosswalk values, K, and DEF.
- Add synthetic fixtures and offline tests for successful, unresolved, conflicting, and
  type/season-invalid mappings.

## Out of scope

- Sleeper host permissions, service-worker requests, browser UI, polling, or draft observation.
- Adding `sleeper` to the OpenAPI protocol or backend runtime transport.
- Name-based auto-resolution, a live family-league capture, or retention of raw player catalog
  payloads in version control.

## Discovery progress

The existing `IdentityPipeline` already enforces unique exact mappings, asset-type consistency,
team-defense validity seasons, explicit overrides, and unresolved/conflict outcomes. It has no
Sleeper catalog builder and current curated-player records retain `gsis_id` but not the nflverse
ESPN identifier needed for a second exact corroboration route.

A read-only, non-retained catalog comparison on 2026-08-22 found partial active-record coverage
against the current nflverse player file: exact GSIS/ESPN corroboration reached 143 QB, 251 RB,
474 WR, 252 TE, and 59 K records. The catalog contained 32 active `DEF` team-code records. These
figures prove that automatic catalog-field matching alone cannot satisfy the supported prepared
pool: the implementation must retain exact authoritative identifiers, detect disagreement, and
publish an explicit override/unresolved report rather than guess from names.

The first implementation slice now retains nflverse `espn_id` in curated player records, parses a
local Sleeper catalog snapshot into only provider ID, position, team, GSIS, and ESPN fields, and
builds mappings only where every supplied authoritative identifier converges on one matching
position/team asset. It enforces exact team-defense season validity and reports unresolved and
conflicting references. The source-manifest boundary now supports the documented public catalog as
a local JSON snapshot and the report writer persists deterministic mapping/coverage evidence with
the pinned source-manifest identifier. Synthetic unit tests cover K, DEF, a missing identifier,
disagreement, a changed catalog key, and JSON source snapshots. Applying this to a real prepared
pool and publishing its coverage report remains pending.

The local review workflow now writes an ignored candidate queue and exposes `sleeper-review next`,
`status`, `approve`, and `approve-batch` commands. Approval requires the queue's exact Sleeper ID
and internal candidate ID plus a reviewer and reason; a candidate cannot be silently accepted,
re-approved, or substituted with a different internal asset. Batch approval only includes
still-pending one-to-one name/team/position suggestions with no provider GSIS or ESPN value. It
previews the count and writes decisions only after `--confirm`; conflicts, authoritative-ID cases,
and DEF remain outside the batch.

The validation command now requires a local curated-player Parquet artifact, catalog manifest and
snapshot, review queue, and decisions. It verifies the snapshot checksum, queue provenance, exact
candidate target, all asset/season invariants, and no contradiction with exact catalog evidence;
its deterministic report records all three local input checksums. Generating and evaluating the
real local report remains pending.

Prepared-pool coverage is now a required input to crosswalk validation. The command accepts only
the version directory of an immutable published dataset, verifies every manifest output checksum,
then verifies the declared `prepared.parquet` checksum, row count, and row-level dataset/feature
versions before pinning those versions in the report. Every internal pool asset must appear in the
crosswalk; the command fails before writing a report if any asset is unmapped. No current 2026
published prepared-pool version exists locally yet, so final publication evidence remains pending.

After validation, `sleeper-crosswalk publish` derives a *new* immutable dataset version from that
prepared version. It re-pins its prepared rows to the new version, copies the verified inherited
outputs, and adds `asset_external_ids.parquet` (unique Sleeper provider/external-ID mappings with
method, provenance, asset type, validity state, and season) plus
`sleeper_crosswalk_coverage.parquet`. The original dataset remains unchanged. This publication
path is covered with a synthetic dataset; it cannot run until the real 2026 prepared version is
available.

## Acceptance criteria

- [ ] The published crosswalk has unique `(provider="sleeper", external_id)` keys, asset-type
  consistency, provenance, validity state, and a pinned version.
- [ ] Individual-player matches require an exact corroborated route; missing or conflicting catalog
  values remain unresolved or conflict rather than matching by name.
- [ ] DEF resolves only through an exact provider-team/NFL-team/season-valid mapping; K resolves as
  an individual player.
- [ ] Coverage and conflict checks quantify every supported position and fail publication when a
  required asset is unmapped or ambiguous.
- [ ] Synthetic fixtures and tests cover K, DEF, rookies, duplicate names, missing IDs, and
  stale/changed mappings without a live Sleeper request.
- [ ] Canonical data, source-inventory, domain, and operational documentation remain aligned.

## Validation

- [ ] Run applicable backend formatting, lint, type, test, build, documentation, and OpenAPI
  contract checks.
- [ ] Verify the test suite executes only from synthetic/local fixtures and no restricted or raw
  provider payload is committed.

## Blocker

The original local Sleeper catalog snapshot no longer matches the checksum recorded in its source
manifest. The user approved a renewed local queue built from a fresh verified snapshot: 897 of 899
approved decisions retained the same candidate internal IDs. The user explicitly reviewed the two
changed player-team records and approved timestamped team-transition overrides that preserve the
conflicting nflverse roster evidence. The validated local report maps 936 assets without conflict,
including all 32 current-season DEF identities.

An operator-authorized extension inspection then supplied the missing private league configuration:
eight teams, snake redraft, 1 QB/2 RB/2 WR/1 TE/1 WR-RB flex/1 K/1 DEF/4 BN, with non-flat
field-goal and defense scoring. The operator explicitly chose to preserve those semantics. A real
prepared dataset cannot be built or validated until NFL-0041 supplies exact neutral scoring and
curated K/DEF inputs for that configuration. Do not publish this report or initialize a live draft
until NFL-0041 is complete and prepared-pool coverage is checked. If source terms, catalog shape,
or authoritative identifier coverage changes, stop publication and record the changed evidence
before substituting a mapping strategy.

## Completion summary

Complete when closing the ticket, including the published-version evidence, coverage report, test
results, and confirmation that unresolved references fail safely.

## History

- 2026-08-22 — Created from NFL-0037's completed identity safe-stop finding.
- 2026-08-22 — Confirmed that the existing exact-resolution machinery is reusable, but catalog
  coverage is partial and the curated schema lacks an ESPN corroboration field; recorded the
  required explicit mapping/reporting path before implementation.
- 2026-08-22 — Added the local catalog parser and exact crosswalk builder; targeted backend
  formatting, lint, type, and test checks passed (65 tests).
- 2026-08-22 — Added the documented catalog source fetcher and deterministic crosswalk-report
  artifact; full backend and documentation checks passed (66 tests).
- 2026-08-22 — Generated a local candidate queue from the public catalog and current nflverse
  identity records; added the explicit local review CLI. No candidate has been approved yet.
- 2026-08-23 — Added a preview-first, explicitly confirmed batch action for candidates that meet
  the narrow manual-review eligibility rule; no local approval decisions were written.
- 2026-08-23 — Added the checksum-pinned local crosswalk validation command and synthetic
  validation coverage; the current reviewed decision set has not yet been promoted.
- 2026-08-23 — Validation correctly rejected the earlier catalog snapshot because its payload
  checksum no longer matches its manifest. A newly retrieved verified catalog preserves 897/899
  approved candidate targets; two require renewed review before a local crosswalk can be built.
- 2026-08-23 — With user confirmation, created a new checksum-pinned queue and renewed 897
  unchanged decisions without overwriting the prior local artifacts. The verified report maps 902
  individual-player assets with no conflict; two changed records remain unresolved, and zero of 32
  Sleeper DEF records map because the current local player artifact has no 2026 team-defense asset.
- 2026-08-23 — Added structural 2026 DEF identities from exact catalog team codes (no fabricated
  performance data); the verified report now maps all 32 DEF records and 934 assets total, with
  zero conflicts. The two changed player-team records remain blocked because the current nflverse
  roster snapshot independently disagrees with Sleeper on both team assignments.
- 2026-08-23 — User explicitly confirmed both changed teams; recorded two separate, timestamped
  team-transition reviews that retain the nflverse disagreement. The checksum-pinned report now
  maps 936 assets with zero conflicts. Prepared-pool coverage remains the final validation gap.
- 2026-08-23 — Added typed prepared-pool coverage validation; synthetic tests prove an unmapped
  prepared asset fails before report publication. A real 2026 prepared-pool artifact is not
  present locally, so the final report/publish gate remains intentionally open.
- 2026-08-23 — Tightened the coverage input to a checksum-verified immutable dataset version;
  its prepared output's row count and row-level dataset/feature versions must agree with the
  manifest, and those versions are pinned in the local crosswalk report. No such real 2026
  prepared dataset version exists locally.
- 2026-08-23 — Added immutable crosswalk publication: a checked parent prepared version is copied
  into a new version with re-pinned prepared rows, canonical external-ID mappings, and coverage
  evidence. Synthetic publication tests pass; real 2026 source/scoring/preparation inputs remain
  required before promotion.
- 2026-08-23 — Operator authorized local extension inspection of the test league and chose to
  preserve its exact K/DEF scoring. Moved to Blocked on NFL-0041 rather than asking the operator to
  simplify field-goal and defensive points-allowed bands.
