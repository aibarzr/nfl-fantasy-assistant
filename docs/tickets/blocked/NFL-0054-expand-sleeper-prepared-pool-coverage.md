# NFL-0054 — Expand Sleeper prepared-pool coverage

- Status: Blocked
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0039, NFL-0042, NFL-0045

## Canonical sources

- [MVP Specification — Draft observation and identity](../../product/mvp-spec.md#functional-requirements)
- [Data and Player Identity — Prepared and runtime identity](../../data/data-and-identity.md#identity-resolution)
- [Domain Model — Identity resolution](../../domain/domain-model.md#identity-resolution)
- [Development Guide — Data and model tests](../../engineering/development.md#tests)

## Outcome

Publish a new immutable Sleeper prepared dataset that covers every locally verified, crosswalk-resolved
current-season asset with usable historical features, so a valid live pick cannot become unresolved
merely because it fell outside the previous Top-300 recommendation pool.

## Context

Live validation found two already-drafted Sleeper references outside the activated 300-player
prepared pool. The existing runtime intentionally persists exact IDs only for prepared assets, so
it safely paused rather than guessing. The operator authorized a full-coverage replacement dataset.

## In scope

- Rebuild the current prepared pool at full local crosswalk coverage from existing verified inputs.
- Validate and publish a new immutable crosswalk-derived dataset version.
- Verify that the previously unresolved live references are represented without retaining them in
  documentation or committed artifacts.
- Record safe activation and fresh-session requirements.

## Out of scope

- Altering a published dataset, identity guessing, exporting private draft data, or deleting the
  existing local draft state without separate operator confirmation.

## Acceptance criteria

- [ ] A new immutable prepared and crosswalk dataset validates all source, checksum, identity,
  projection, and recommendation-input gates.
- [ ] The verified live unresolved-reference count against the new runtime identity table is zero.
- [ ] The existing dataset remains unchanged and no private data is committed.

## Validation

- [ ] Run applicable data/runtime checks and repository quality gates.
- [ ] Record the new local version and activation procedure without credentials or draft identifiers.

## Blocker

The full verified rebuild produces 581 feature-ready assets, not all 936 crosswalk-resolved
assets. It covers one of the two live unresolved references; the remaining reference has no usable
historical feature record and cannot receive a fabricated projection. Publishing this version would
leave the live draft non-current. To resume, approve an identity-only runtime path for
already-drafted, unscored assets, or provide an approved feature/projection source for the missing
asset.

## Completion summary

Complete when closing the ticket with local publication and validation evidence.

## History

- 2026-08-23 — Started after the operator approved a full-coverage immutable replacement dataset
  following live identity-gate validation.
- 2026-08-23 — Blocked after the verified full rebuild produced 581 feature-ready assets and left
  one of two live unresolved references outside the prepared pool. No incomplete dataset was
  activated or used to modify the existing draft state.
