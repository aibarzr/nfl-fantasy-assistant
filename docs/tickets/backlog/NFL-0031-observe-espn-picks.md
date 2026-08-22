# NFL-0031 — Implement pick observation, event IDs, and snapshot fallbacks

- Status: Backlog
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Unassigned
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: NFL-0005, NFL-0030

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#primary-user-journey)
- [Extension–Backend Protocol](../../contracts/protocol.md#idempotency-ordering-and-conflicts)

## Outcome

The ESPN adapter emits deterministic neutral pick observations, detects gaps, and supplies complete-enough snapshots for safe backend reconciliation.

## Scope

Implement structured-first observation, stable `event_id` creation, duplicate suppression as an optimization, periodic snapshots, completeness declaration, and adapter incompatibility handling.

## Acceptance criteria

- [ ] The same ESPN pick context always produces the same stable event ID.
- [ ] Reload or repeated observation can resend safely and never assumes extension memory is canonical.
- [ ] Missed/gapped observations trigger snapshot recovery rather than local reordering or guessing.
- [ ] Adapter failure stops further mutation from that source and preserves diagnostic evidence safely.

## Validation

- [ ] Test sequential, duplicate, missed, delayed, reloaded, worker-suspended, and incompatible fixture flows.
- [ ] Confirm emitted payloads contain observed facts only and no sensitive page data.

## History

- 2026-07-29 — Created in Backlog.
