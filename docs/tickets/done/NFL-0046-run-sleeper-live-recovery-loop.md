# NFL-0046 — Run Sleeper live recovery loop

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0037, NFL-0043, NFL-0044, NFL-0045

## Canonical sources

- [MVP Specification — Primary user journey and recovery](../../product/mvp-spec.md#primary-user-journey)
- [Architecture Overview — Runtime flows](../../architecture/overview.md#runtime-flows)
- [Protocol — Sleeper complete snapshots](../../contracts/protocol.md#neutral-references-and-observations)
- [Source inventory — Sleeper read-only API](../../data/source-inventory.md#approved-for-bounded-recovery-validation-and-local-identity-mapping-sleeper-read-only-api)
- [Threat model](../../security/threat-model.md#threat-scenarios)

## Outcome

The active supported Sleeper draft page safely polls a bounded read-only recovery source, submits
new picks idempotently, reconciles the complete snapshot, and renders the backend’s current Top-N
recommendation response in the existing isolated panel.

## Context

Initialization and backend recommendation generation are complete, but the content lifecycle does
not yet connect either of them to a live recovery/update loop. The extension remains an adapter and
renderer; it does not own canonical picks, player identity, or recommendation calculations.

## In scope

- A service-worker-only, exact-surface Sleeper sync operation using validated complete snapshots.
- Bounded polling with capped exponential backoff and clear non-current UI state on failures.
- Stable event submission for new contiguous picks, followed by authoritative snapshot reconciliation.
- Rendering the current backend recommendation snapshot after initialization and each successful sync.

## Out of scope

- Browser or platform automation of a pick, new provider permissions, raw response retention, or
  a new data/model source.
- ESPN lifecycle work or the full manual end-to-end acceptance/release walkthrough.

## Acceptance criteria

- [x] Only the service worker calls the documented Sleeper recovery endpoints, from the exact active draft surface and at the documented bounded rate.
- [x] New observed picks use stable event IDs; unsafe, throttled, or malformed recovery data causes no backend mutation and backs off visibly.
- [x] Every successful cycle reconciles the complete snapshot and renders only a current backend recommendation response.
- [x] Reload and worker restart resume from the canonical backend draft without extension-owned draft state.
- [x] Synthetic tests and canonical documentation cover normal polling, failures/backoff, idempotency, recovery, and panel states.

## Validation

- [x] Extension format/lint/type checks and 56 tests passed; documentation checks and `git diff --check` passed.
- [x] Confirmed no live league data, identifiers, credentials, or generated artifacts were committed; final full quality/drift checks run after commit.

## Completion summary

Added a worker-owned `sleeper_sync` operation that validates the exact active surface, reads a
complete documented recovery snapshot, sends stable event IDs only for new contiguous picks, and
reconciles the full snapshot. The content lifecycle immediately renders current backend
recommendations after initialization, then runs a five-second recovery loop with capped
exponential backoff and visible non-current states. No draft state is retained in the extension.
Synthetic tests cover the success path, safe-stop behavior, event ID, retry/backoff cap, and panel
refresh. The source inventory records the bounded rate using current official Sleeper guidance.

## History

- 2026-08-23 — Created in progress after Sleeper runtime recommendation activation.
- 2026-08-23 — Completed with service-worker-only sync/reconciliation, current panel refresh, and
  bounded provider polling/backoff.
