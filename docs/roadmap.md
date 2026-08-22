# Roadmap

## Current status

**Phase 5 — live platform loops.** In progress as of 2026-08-22. The extension has a checked,
service-worker-only localhost client and a read-only, explainable recommendation panel. Trusted
ESPN surface activation and local security controls are complete, but league initialization remains
blocked because the canonical sanitized findings do not establish an active-user team/slot source,
semantic roster/scoring codebook, or authoritative recovery snapshot/replay. Sleeper is an
approved second provider: its extension-bound, read-only API design is recorded in ADR-0002 and
its discovery spike must complete before runtime implementation. K and DEF are supported MVP
assets with completed neutral domain/data/model support; Sleeper still needs adapter-specific
identity and recovery evidence before a league with those positions can initialize. The Phase 4
recommendation engine is complete.

## Delivery phases

1. **Technical spikes:** validate provider draft observability, player IDs, nflverse mappings,
   league settings, draft order, and approved data sources. Keep captures sanitized and produce
   narrow findings or ADRs.
2. **Data foundation:** ingest through nflreadpy, curate Parquet datasets, build identity mappings and weekly features, calculate league scoring, and output roughly 250–350 baseline-ranked players.
3. **Backend draft core:** add FastAPI, SQLite persistence, domain models, event processing, reconciliation, and availability calculation, all testable without a browser.
4. **Baseline recommendation engine:** implement deterministic projections, ECR prior, dynamic replacement level/VOR, roster fit, risk, and explanations.
5. **Live platform loops:** implement provider-specific extension adapters, local HTTP transport,
   recovery, and browser recommendation UI over the completed neutral K and team-defense asset
   support. ESPN remains on its existing evidence-gated path;
   Sleeper uses its documented read-only API only through the extension adapter and is accepted
   separately against the same neutral backend protocol.
6. **Recommendation improvements:** strengthen the baseline urgency, tier/scarcity detection, stage-dependent weights, confidence, and rookie handling.
7. **FantasyPros surface:** validate its behavior and add its adapter without duplicating decision logic or changing the neutral backend contract unnecessarily.
8. **Draft simulation:** add Monte Carlo survival and next-pick value only after the deterministic live loop is reliable and measurable.
9. **In-season modules:** consider lineup, waivers, drops, and trades as separate decision engines after draft support is stable.

## Milestone discipline

- A phase may start with spikes, but production code enters only after its relevant contract and acceptance criteria exist.
- Update this document when a phase changes; keep task-level backlog in the [internal ticketing system](tickets/README.md).
- Record costly-to-reverse architectural changes as ADRs.
- Do not move deferred capabilities into the MVP implicitly.
