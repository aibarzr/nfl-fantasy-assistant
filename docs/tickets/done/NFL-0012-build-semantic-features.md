# NFL-0012 — Build deterministic, time-safe semantic features

- Status: Done
- Resolution: Done
- Phase: 2 — Data foundation
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0010

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#feature-foundation)
- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)

## Outcome

Versioned offline transforms produce stable weekly usage, opportunity, efficiency, role, availability, and high-value-usage features without future leakage.

## Scope

Implement only the semantic inputs required by the deterministic position-specific baseline, with source lineage and explicit observation cutoffs.

## Acceptance criteria

- [x] Feature definitions, units, windows, missingness, version, and source lineage are documented.
- [x] Historical rows use no information unavailable at their declared cutoff.
- [x] Repeated transforms from identical inputs are byte- or value-equivalent under the documented format.
- [x] Historical production is represented once for projection and is not exposed as a duplicate final-score input.

## Validation

- [x] Fixture tests show the first (rookie/insufficient-history) row remains null and later rows
  only consume earlier weeks with an explicit observation cutoff.
- [x] Deterministic sorted transforms, range checks, null semantics, and historic lineage are
  covered by backend tests and quality checks passed on 2026-07-30.

## Completion summary

Implemented feature version 1 with four-game usage, opportunity, efficiency, high-value-use,
role-stability, availability, and one historical-production measure. The transform has no access
to the target week and preserves unavailable history rather than converting it into zero.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex; validation evidence recorded above.
