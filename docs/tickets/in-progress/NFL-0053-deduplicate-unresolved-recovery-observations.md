# NFL-0053 — Deduplicate unresolved recovery observations

- Status: In Progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0046

## Canonical sources

- [MVP Specification — Degraded and failure behavior](../../product/mvp-spec.md#degraded-and-failure-behavior)
- [Domain Model — Reconciliation semantics](../../domain/domain-model.md#reconciliation-semantics)
- [Extension–Backend Protocol — Idempotency, ordering, and conflicts](../../contracts/protocol.md#idempotency-ordering-and-conflicts)

## Outcome

A repeated complete recovery snapshot records an unresolved player fact once, leaving the draft
paused for mapping resolution without growing canonical unresolved-observation history.

## Context

Live recovery correctly surfaced two unknown player references, but every polling cycle appended
the same unresolved facts. That harms diagnostics and violates the observation's repeatable,
idempotent intent without making recommendations safer.

## In scope

- Deduplicate exact unresolved pick/team/provider/reference facts during snapshot reconciliation.
- Preserve the non-current state and report the unresolved pick in reconciliation differences.
- Add deterministic service coverage and document the invariant.

## Out of scope

- Automatic identity guessing, raw provider payload retention, or mutable changes to a published
  dataset.

## Acceptance criteria

- [ ] Replaying an identical recovery snapshot with an unknown reference leaves one unresolved
  canonical observation.
- [ ] A repeated unknown keeps recommendations paused and does not modify accepted availability.
- [ ] Domain documentation and backend tests record the idempotency rule.

## Validation

- [ ] Run applicable backend and repository quality checks.
- [ ] Confirm no live league data, credentials, or generated artifacts are committed.

## Blocker

None.

## Completion summary

Complete when closing the ticket with test and live-safe evidence.

## History

- 2026-08-23 — Started after live Sleeper recovery exposed repeated storage of the same unresolved
  provider facts.
