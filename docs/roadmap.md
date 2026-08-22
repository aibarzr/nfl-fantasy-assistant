# Roadmap

## Current status

**Phase 5 — ESPN live loop.** In progress as of 2026-07-31. The extension now has a checked,
service-worker-only localhost client and a read-only, explainable recommendation panel. Trusted
ESPN surface activation and local security controls are complete. League initialization remains
blocked because the canonical sanitized findings do not yet establish an active-user team/slot
source, semantic roster/scoring codebook, or authoritative recovery snapshot/replay. The Phase 4
recommendation engine is complete.

## Delivery phases

1. **Technical spikes:** validate ESPN draft observability, player IDs, nflverse mappings, league settings, draft order, and approved data sources. Keep captures sanitized and produce narrow findings or ADRs.
2. **Data foundation:** ingest through nflreadpy, curate Parquet datasets, build identity mappings and weekly features, calculate league scoring, and output roughly 250–350 baseline-ranked players.
3. **Backend draft core:** add FastAPI, SQLite persistence, domain models, event processing, reconciliation, and availability calculation, all testable without a browser.
4. **Baseline recommendation engine:** implement deterministic projections, ECR prior, dynamic replacement level/VOR, roster fit, risk, and explanations.
5. **ESPN live loop:** implement the ESPN adapter, HTTP client, recovery, and browser recommendation UI.
6. **Recommendation improvements:** strengthen the baseline urgency, tier/scarcity detection, stage-dependent weights, confidence, and rookie handling.
7. **FantasyPros surface:** validate its behavior and add its adapter without duplicating decision logic or changing the neutral backend contract unnecessarily.
8. **Draft simulation:** add Monte Carlo survival and next-pick value only after the deterministic live loop is reliable and measurable.
9. **In-season modules:** consider lineup, waivers, drops, and trades as separate decision engines after draft support is stable.

## Milestone discipline

- A phase may start with spikes, but production code enters only after its relevant contract and acceptance criteria exist.
- Update this document when a phase changes; keep task-level backlog in the [internal ticketing system](tickets/README.md).
- Record costly-to-reverse architectural changes as ADRs.
- Do not move deferred capabilities into the MVP implicitly.
