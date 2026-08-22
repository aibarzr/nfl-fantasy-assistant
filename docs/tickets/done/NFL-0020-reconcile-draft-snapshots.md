# NFL-0020 — Implement snapshot reconciliation and blocked/conflict states

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0019

## Canonical sources

- [Domain Model](../../domain/domain-model.md#reconciliation-semantics)
- [Architecture Overview](../../architecture/overview.md#reconcile-and-recover)

## Outcome

Declared-completeness snapshots repair only unambiguous missing picks and block freshness when accepted history conflicts.

## Scope

Implement `POST /v1/drafts/{draft_id}/snapshot`, difference classification, ordered append/rebuild, partial-snapshot handling, conflict persistence, and reconciliation diagnostics.

## Acceptance criteria

- [x] Identical picks are no-ops and unambiguous missing picks append in order atomically.
- [x] Incomplete snapshots cannot delete accepted trailing history.
- [x] Conflicting team/player at an accepted pick blocks fresh recommendations without replacing history.
- [x] Source, timestamp, declared scope/completeness, differences, and outcome are persisted.

## Validation

- [x] `test_draft_service.py` covers missed-pick, partial, conflicting, unresolved identity and
  rollback-backed reconciliation behavior; domain tests cover deterministic rebuild derivations.
- [x] Reconciliation records and state transition persist in one SQLite transaction; full quality
  checks passed on 2026-07-30.

## Completion summary

Implemented `/v1/drafts/{draft_id}/snapshot`, persisted difference/outcome records, append-only
repair, partial evidence preservation, and blocked conflict state.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
