# NFL-0009 — Implement source manifests and raw nflverse ingestion

- Status: Done
- Resolution: Done
- Phase: 2 — Data foundation
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0001, NFL-0008

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#data-lifecycle)
- [Development Guide](../../engineering/development.md#configuration-and-sensitive-material)

## Outcome

Offline ingestion creates immutable local raw snapshots and manifests with source, retrieval, checksum, schema, and licensing metadata.

## Scope

Use nflreadpy/nflverse for approved 2022–2025 inputs, separate replaceable cache from raw snapshots, and keep source-shaped records inside the backend data layer.

## Acceptance criteria

- [x] Repeating ingestion of the same source version produces the same manifest identity.
- [x] Partial or failed retrieval never appears as a complete snapshot.
- [x] Raw data and caches use configured local paths and remain ignored by VCS.
- [x] Small redistributable fixtures exercise the same ingestion boundary in tests.

## Validation

- [x] `backend/tests/test_data_foundation.py` exercises successful repeated and failed fixture
  retrieval; source identity contains resolved source, version, schema, checksum, license, and
  consumed-column provenance.
- [x] `./scripts/quality.sh all` passed on 2026-07-30. Local `data/*` remains ignored; the source
  snapshot has no Git metadata, so its drift check was correctly skipped.

## Completion summary

Added an injectable `nflreadpy` outer adapter and immutable local snapshot ingestor. Source payload
is durably written before the manifest, and only the complete manifest makes a snapshot usable.
Identity hashing excludes retrieval time, making repeated input identity stable; caches/raw paths
are constructor-configured and remain local.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex; validation evidence recorded above.
