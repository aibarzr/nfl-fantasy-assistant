# NFL-0035 — Prove deterministic end-to-end recovery and sub-second performance

- Status: Backlog
- Resolution: Unresolved
- Phase: 5 — ESPN live loop
- Owner: Unassigned
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: NFL-0020, NFL-0023, NFL-0028, NFL-0031, NFL-0032, NFL-0033, NFL-0034

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#acceptance-criteria)
- [Development Guide](../../engineering/development.md#integration-and-performance)

## Outcome

The deterministic sanitized 8-team ESPN fixture proves the complete observation-to-render MVP,
recovery behavior, reproducibility, and local update budget.

## Scope

Exercise known player pools, configuration/order/user slot, picks, duplicate event, missed pick, unknown identity, conflicts, page/worker/backend restart, recommendations, provenance, and latency.

## Acceptance criteria

- [ ] Picks are detected, identified, persisted, and removed from canonical availability exactly once.
- [ ] Duplicate and missed-event reconciliation preserve valid state; unresolved conflicts block freshness.
- [ ] Page, worker, and backend restarts resume the same draft and recommendation revision safely.
- [ ] The deterministic Top-N is league-aware, explainable, replayable, and event-to-render completes under one second excluding platform delay.

## Validation

- [ ] Run the deterministic 8-team league fixture repeatedly and record functional and latency results.
- [ ] Replay stored inputs under pinned versions and compare rankings, components, and provenance.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Corrected fixture scope to the canonical 8-team MVP; the prior 10/12-team wording was not authoritative.
