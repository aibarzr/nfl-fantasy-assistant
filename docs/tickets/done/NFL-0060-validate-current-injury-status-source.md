# NFL-0060 — Validate and govern a current injury-status source

- Status: Done
- Resolution: Done
- Phase: 6 — Recommendation improvements
- Owner: Codex
- Created: 2026-08-24
- Updated: 2026-08-24
- Depends on: NFL-0037, NFL-0039

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#sources-and-compliance)
- [Phase 1 Source Inventory](../../data/source-inventory.md#approved-for-bounded-recovery-validation-and-local-identity-mapping-sleeper-read-only-api)
- [Phase 1 Source Inventory](../../data/source-inventory.md#future-source-admission-checklist)
- [Security Threat Model](../../security/threat-model.md)

## Outcome

A written, evidence-backed source decision either approves a narrowly bounded current player-status
feed for recommendation risk or records why it remains excluded, with no production behavior
enabled by assumption.

## Context

The Sleeper player catalog currently serves an approved identity and display-label purpose only;
its fields are explicitly excluded from projection and valuation. Its documented player records
include status, injury status/start date, practice participation, and depth-chart facts, but their
actual current semantics, freshness, stability, terms, and identity coverage have not been
validated for model use. nflverse exposes an injury loader, but the project's source inventory
records a 2025 coverage gap.

## In scope

- Verify exact candidate endpoint(s), owner, terms, permitted use, consumed fields, request cadence,
  timestamps, retention, attribution, redistribution, and failure behavior.
- Inspect only authorized, read-only responses and retain only sanitized schema/enum examples,
  checksums, counts, freshness evidence, and mapping coverage needed for the decision.
- Measure null rates, enum/value stability, update timing, current-player coverage, exact-ID
  alignment, contradictory status fields, and behavior for IR/PUP/NFI/suspension/free-agent cases.
- Define provider-to-neutral status translation candidates and explicitly separate observed status
  from medical prognosis and historical durability.
- Update the canonical source inventory and related data/security documentation with an approval,
  bounded approval, or rejection and its re-review condition.

## Out of scope

- Changing the protocol, persistence, projection, valuation, ranking, or extension runtime.
- Scraping news, reports, authenticated pages, or undocumented endpoints.
- Assigning fantasy-value penalties or predicting recovery dates.

## Acceptance criteria

- [x] The source decision names exact endpoints and fields, terms evidence and review date,
  non-commercial constraints, cadence/rate limits, retention, provenance, and failure behavior.
- [x] Sanitized evidence covers representative healthy, questionable, doubtful, out, reserve,
  missing, stale, and contradictory records without retaining real private-league payloads.
- [x] Every accepted record joins by an exact reviewed provider identity; names are never used as a
  primary mapping or critical fallback.
- [x] The decision defines freshness thresholds and requires missing or stale status to remain
  unknown rather than healthy.
- [x] No production source use is enabled unless the canonical inventory explicitly approves it.

## Validation

- [x] Run `./scripts/quality.sh docs` and any source-specific sanitization/checksum validation
  introduced by the spike.
- [x] Confirm no credentials, raw catalogs, real private-league data, restricted datasets, or
  sensitive artifacts were committed.

## Completion summary

Approved a bounded once-daily Sleeper player-status overlay. The source finding records endpoint,
fields, aggregate schema/enum evidence, non-commercial terms, exact-ID joining, retention,
freshness (36 hours), unknown/conflict behavior, and re-review conditions. The canonical inventory
and threat model now authorize only the reduced neutral overlay. A synthetic sanitized fixture
covers healthy, questionable, doubtful, out, reserve, missing, stale, and conflicting cases.
`./scripts/quality.sh docs` passed.

## History

- 2026-08-24 — Created in Backlog as the required source-governance gate for current injury-aware
  recommendations.
- 2026-08-24 — Started with a documented, read-only status-schema and enum audit.
- 2026-08-24 — Completed with bounded source approval and sanitized validation evidence.
