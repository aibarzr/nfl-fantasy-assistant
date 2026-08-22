# NFL-0019 — Implement idempotent event ingestion and canonical revisions

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0018

## Canonical sources

- [Extension–Backend Protocol](../../contracts/protocol.md#idempotency-ordering-and-conflicts)
- [Domain Model](../../domain/domain-model.md#invariants)

## Outcome

`POST /v1/drafts/{draft_id}/events` applies each valid observation exactly once and returns a stable outcome and resulting canonical revision.

## Scope

Implement event validation, identity resolution, ordering checks, atomic state/outcome persistence, replay, payload-conflict, gap, and complete-draft behavior.

## Acceptance criteria

- [x] Replaying the same semantic `event_id` returns its established outcome without a second transition.
- [x] Reusing an ID with materially different data returns `409 event_id_conflict` and preserves state.
- [x] Accepted picks obey configured order, unique overall pick and player invariants.
- [x] Gaps and unresolved players retain observations and request reconciliation without guessed availability changes.

## Validation

- [x] `test_draft_service.py`, `test_api.py`, and `test_sqlite_persistence.py` cover success,
  duplicate/conflicting replay, gaps, unresolved players, rollback failure, completion invariants,
  and unique persisted event outcomes.
- [x] SQLite unique constraints and atomic transition/outcome commits prevent duplicate effects.

## Completion summary

Implemented semantic event fingerprints and atomic idempotent `/v1/drafts/{draft_id}/events`
processing with canonical revisions and explicit reconciliation outcomes.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
