# NFL-0005 — Validate ESPN draft observability and extraction fallbacks

- Status: Done
- Resolution: Done
- Phase: 1 — Technical spikes
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: None

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#functional-requirements)
- [Architecture Overview](../../architecture/overview.md#platform-adapter-strategy)
- [Development Guide](../../engineering/development.md#fixtures-and-live-investigation)

## Outcome

A narrow, dated finding establishes which ESPN draft observations are available through structured APIs, page-consumed responses, browser state, and DOM fallback.

## Scope

Inspect only authorized browser-visible behavior needed for initialization, picks, and reconciliation. Retain minimal sanitized evidence that can drive offline adapter tests.

## Acceptance criteria

- [x] The finding ranks viable observation mechanisms and states completeness and failure limitations for each.
- [x] Required facts for initial snapshot, pick event, and recovery snapshot are mapped to observed sources or to the explicitly unavailable recovery outcome.
- [x] Any committed fixture is sanitized and records surface, capture date, completeness, and expected parser outcome.
- [x] Unknown or incompatible page shapes have an explicit safe-stop strategy.

## Validation

- [x] Reviewed captures; committed derivatives contain no cookies, tokens, direct account/league/team IDs, names, or unrelated fields, and the fixture checker enforces those exclusions.
- [x] Reviewed the canonical architecture: the finding confirms its existing adapter order, so no boundary change or ADR is required.

## Completion summary

[`ESPN draft observability finding — 2026-07-30`](../../espn-data/observability-finding-2026-07-30.md)
records the observed structured configuration response and WebSocket `SELECTED` stream. The
complete captured stream can derive an ordinal only while it remains contiguous and matches the
scheduled order. No authoritative-enough reload/missed-event recovery snapshot was observed, so
the adapter must block freshness and request reconciliation instead of guessing. Sanitized fixture
validation passes with `node scripts/check_espn_spike_fixtures.mjs`.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-29 — Started by Codex; no fixture or authorized draft evidence was available.
- 2026-07-29 — Blocked pending an authorized session or sanitized initialization, pick, and recovery captures.
- 2026-07-30 — Reopened by Codex after sanitized 8-team structured-response and WebSocket fixtures became available.
- 2026-07-30 — Completed by Codex with a safe-stop finding for the unobserved recovery source.
