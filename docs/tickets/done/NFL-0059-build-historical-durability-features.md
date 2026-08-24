# NFL-0059 — Build evidence-backed historical durability features

- Status: Done
- Resolution: Done
- Phase: 6 — Recommendation improvements
- Owner: Codex
- Created: 2026-08-24
- Updated: 2026-08-24
- Depends on: NFL-0058

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#initial-coverage-and-freshness)
- [Data and Player Identity](../../data/data-and-identity.md#feature-foundation)
- [Phase 1 Source Inventory](../../data/source-inventory.md#future-source-admission-checklist)
- [Offline Data Contract](../../data/offline-data-contract.md#identity-and-features)
- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)

## Outcome

The offline data pipeline produces versioned, time-safe durability and participation-proxy
features that distinguish supported participation, supported absence, bye weeks, and unknown
evidence without claiming an injury diagnosis.

## Context

Player-stat rows alone cannot distinguish injury, a healthy inactive designation, a backup with no
usage, a bye, or missing data. The approved nflverse roster, snap, depth-chart, schedule/game, and
historical injury routes have different coverage and licenses. Their exact use and gaps must be
defined before a historical durability signal can influence projections.

## In scope

- Admit or reject each required nflverse input in the source inventory with exact retrieval,
  fields, identity keys, cadence, license, historical coverage, missingness, and failure behavior.
- Construct a player-team-week eligibility calendar that excludes byes and never treats an absent
  stat row alone as proof of injury or inactivity.
- Define tri-state participation evidence and separately named durability, recent-participation,
  and role/snap-stability features.
- Evaluate transparent 4-game, 8-game, prior-season, and multi-season recency windows without
  future leakage; choose and version only configurations supported by backtest evidence.
- Preserve source timestamps and lineage and fail publication when declared evidence coverage is
  incomplete or internally contradictory.

## Out of scope

- Diagnosing injury type, body part, recurrence, recovery date, or medical prognosis from inferred
  participation.
- Treating a bye, roster absence, zero-touch game, or missing source row as interchangeable.
- Ingesting current Sleeper medical status or changing the live extension/backend protocol.

## Acceptance criteria

- [x] Canonical data, source-inventory, offline-contract, and modeling documentation define the
  admitted evidence, stable semantics, null behavior, and intended projection use before code
  consumes it.
- [x] The transform distinguishes bye, supported participation, supported non-participation, and
  unknown evidence with exact player/team/season/week identity and lineage.
- [x] Feature windows use only information available at their declared cutoff and retain prior
  seasons without allowing a missing week to collapse calendar time silently.
- [x] Fixture coverage includes bye weeks, roster changes, zero-usage appearances, missed games,
  backups, incomplete source coverage, and contradictory identity evidence.
- [x] Projection/backtest reports show feature coverage and effects by position and confidence;
  unsupported segments remain null rather than receiving fabricated durability.

## Validation

- [x] Run applicable ingestion, curation, feature, projection, publication, leakage, determinism,
  and backtest checks plus `./scripts/quality.sh backend` and `./scripts/quality.sh docs`.
- [x] Rebuild twice from the same manifests and compare features, warnings, prepared values, and
  checksums.
- [x] Confirm no generated, local, restricted, or sensitive artifacts were committed.

## Completion summary

Implemented a typed, exact player/team/week eligibility calendar and time-safe durability windows.
Byes are excluded; supported participation, no-snap participation proxy, and unknown evidence
remain distinct. Incomplete windows stay null. The offline current-pool command now accepts an
optional checksum-verified participation-calendar snapshot and carries its lineage into publication.
Durability remains unpromoted (and therefore has no projection/ranking effect) until NFL-0062's
segmented promotion gate. Fixture tests cover calendar completeness, roster ambiguity, bye, zero
snaps, missing evidence, cutoff safety, and multi-season rates. Backend checks and docs checks pass.

## History

- 2026-08-24 — Created in Backlog to replace the current binary availability approximation with
  evidence-backed durability semantics.
- 2026-08-24 — Started after NFL-0058 corrected fabricated availability semantics.
- 2026-08-24 — Completed with evidence-backed calendar/durability transforms and optional
  versioned prepared-pool integration.
