# NFL-0052 — Normalize Sleeper current-pick snapshots

- Status: In Progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0040, NFL-0046

## Canonical sources

- [MVP Specification — Draft observation and recovery](../../product/mvp-spec.md#functional-requirements)
- [Domain Model — Reconciliation semantics](../../domain/domain-model.md#reconciliation-semantics)
- [Extension–Backend Protocol — Neutral references and observations](../../contracts/protocol.md#neutral-references-and-observations)

## Outcome

The Sleeper adapter accepts a complete current provider snapshot during any point of an active
eight-team snake draft, irrespective of transport order or numeric roster-ID representation, while
still refusing a gap, duplicate, invalid snake slot, or slot-to-roster mismatch.

## Context

Live validation exposed a current documented picks response that did not satisfy the original
fixture's transport assumptions. A complete current snapshot is a contiguous prefix, not a
finished draft or necessarily a round boundary.

## In scope

- Canonicalize validated raw pick records by `pick_no` before contiguity and snake checks.
- Normalize safe numeric provider roster IDs to their neutral string representation.
- Document the distinction between a complete current snapshot and a completed draft.
- Add synthetic coverage for an unordered, mid-round snapshot.

## Out of scope

- Retaining live provider payloads, weakening gap/conflict validation, or changing backend
  canonical-state ownership.

## Acceptance criteria

- [ ] A contiguous active-draft prefix through any current pick validates after canonical ordering.
- [ ] A missing, duplicate, cross-scoped, slot-invalid, or slot-to-roster-inconsistent pick remains
  unavailable and produces no backend mutation.
- [ ] Protocol documentation and synthetic tests describe the current-snapshot semantics.

## Validation

- [ ] Run applicable extension and repository quality checks.
- [ ] Confirm no live league data, credentials, or generated artifacts are committed.

## Blocker

None.

## Completion summary

Complete when closing the ticket with live-safe validation evidence.

## History

- 2026-08-23 — Started after live extension validation exposed a provider transport-shape mismatch
  in the current picks response.
