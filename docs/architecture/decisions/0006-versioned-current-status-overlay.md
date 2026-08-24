# ADR-0006 — Versioned current player-status overlay

- Status: Accepted
- Date: 2026-08-24
- Supersedes: none

## Context

Prepared features and projections are immutable for a draft, while a player's current provider
status changes independently. Sending raw provider records to the backend would cross the adapter
boundary; retaining only a mutable latest value would make a past recommendation unreplayable.

## Decision

The extension's Sleeper adapter reads the approved catalog at most once per UTC calendar day and
reduces requested exact provider IDs to `healthy`, `limited`, `questionable`, `doubtful`, `out`,
`reserve`, `inactive`, or `unknown`. It sends a complete exact-ID overlay with observation time,
source revision, and checksum to the paired backend. The backend validates identity coverage and a
36-hour freshness window, persists semantic revisions immutably, and records the used revision in
recommendation provenance.

Unknown, absent, stale, partial, contradictory, or unsupported source evidence is never healthy.
The overlay is a current fact, not a diagnosis or a change to the pinned prepared dataset.

## Consequences

The backend owns replayable provenance without importing provider fields. The extension retains raw
catalog data only in memory while reducing it. A backend restart reloads the latest valid overlay;
a service-worker restart asks backend provenance before another daily catalog read.

## Alternatives considered

- Backend-side Sleeper calls: rejected because provider behavior remains in the extension adapter.
- Current status in immutable Parquet: rejected because it changes during a draft.
- A mutable latest-only record: rejected because it cannot reproduce a past recommendation.
