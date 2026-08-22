# NFL-0011 — Build identity crosswalk, quarantine, and manual-override workflow

- Status: Done
- Resolution: Done
- Phase: 2 — Data foundation
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0007, NFL-0010

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#identity-resolution)
- [Domain Model](../../domain/domain-model.md#identity-resolution)

## Outcome

A versioned identity pipeline maps provider references to stable internal players, quarantines conflicts, and records auditable manual overrides.

## Scope

Implement unique provider/external-ID mappings, authoritative crosswalks, controlled candidate normalization, provenance, conflict state, and supersession history.

## Acceptance criteria

- [x] Exact mappings are preferred and duplicate provider IDs fail publication.
- [x] Name normalization produces candidates only; auto-resolution requires one corroborated candidate under a versioned rule.
- [x] Unresolved/conflicting references preserve original evidence and do not mutate accepted historical identity.
- [x] Manual overrides include reason, provenance, timestamp, and supersession history.

## Validation

- [x] Tests exercise authoritative mappings, suffix/punctuation normalization, duplicate names,
  missing provider IDs, conflicts, and a documented manual override.
- [x] Internal IDs anchor to GSIS/source IDs rather than names and all resolution outcomes retain
  evidence; backend checks passed on 2026-07-30.

## Completion summary

Added a versioned identity resolver with GSIS/source anchors, exact provider mapping uniqueness,
candidate-only normalized-name fallback requiring team/position corroboration, and explicit
auditable manual override/supersession fields. Ambiguity is quarantined as `unresolved` or
`conflict`, never silently repaired.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex; validation evidence recorded above.
