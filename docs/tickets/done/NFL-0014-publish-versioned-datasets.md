# NFL-0014 — Validate and atomically publish versioned datasets

- Status: Done
- Resolution: Done
- Phase: 2 — Data foundation
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0013

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#quality-gates)
- [Architecture Overview](../../architecture/overview.md#offline-versus-live-processing)

## Outcome

A validated staging build can be atomically promoted to a complete immutable dataset version that new drafts can pin.

## Scope

Implement `dataset_manifest`, schema/checksum/lineage validation, staging publication, active-version selection, and safe retention of the last valid version.

## Acceptance criteria

- [x] Publication requires every documented schema, identity, coverage, missingness, leakage, determinism, lineage, timestamp, and license check.
- [x] Failed or partial builds never replace the last valid published version.
- [x] A draft can pin one dataset/feature version and cannot switch it silently.
- [x] Manifests identify all inputs, transforms, outputs, checksums, and validation results needed for reproduction.

## Validation

- [x] Tests publish a valid fixture version, reject an incomplete validation manifest, preserve the
  old active version, and reject a changed draft pin.
- [x] Staging compares declared files/checksums/row counts against produced bytes before atomic
  promotion; backend and repository quality checks passed on 2026-07-30.

## Completion summary

Implemented staging-directory validation, immutable version promotion by atomic rename, atomic
active-version selection, full reproduction manifests, and explicit dataset/feature version pins.
Failed staging is cleaned up and cannot replace a valid active version.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex; validation evidence recorded above.
