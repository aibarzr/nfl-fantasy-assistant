# NFL-0008 — Validate data sources, licensing, freshness, and market-prior availability

- Status: Done
- Resolution: Done
- Phase: 1 — Technical spikes
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: None

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#sources-and-compliance)
- [Recommendation Engine](../../modeling/recommendation-engine.md#player-value)

## Outcome

An approved source inventory establishes lawful retrieval, storage, transformation, freshness, coverage, and redistribution constraints for nflverse data and any market prior.

## Scope

Record exact datasets/endpoints, owners, terms, retrieval methods, credentials, cadence, gaps, consumed fields, and downstream outputs. This ticket evaluates market data, not the deferred FantasyPros browser surface.

## Acceptance criteria

- [x] Every proposed source has complete provenance and compliance metadata.
- [x] Sources without confirmed permission are excluded from committed or redistributed artifacts.
- [x] Freshness classes and failure behavior are defined for historical, season-state, and market inputs.
- [x] A permitted fallback is documented for missing or stale market data without treating it as zero.

## Validation

- [x] Reviewed the cited nflverse/nflreadpy and FantasyPros terms on 2026-07-29; the source inventory records the evidence locations, review result, and exact exclusions.
- [x] The inventory permits no raw dataset or source credential in the repository; a source-tree review found none.

## Completion summary

Added a dated source inventory. nflverse via nflreadpy is approved for local, provenance-recorded
retrieval subject to per-input attribution/redistribution review. FantasyPros API/data is excluded
until written permission resolves its key, use, distribution, and non-compete restrictions. The
permitted fallback is a marked own-model value with market-component renormalization and a
confidence/freshness warning, never a fabricated zero market value.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-29 — Started by Codex.
- 2026-07-29 — Completed by Codex; validation evidence recorded above.
