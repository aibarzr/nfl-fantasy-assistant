# NFL-0018 — Implement league and draft initialization/resume

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0011, NFL-0015, NFL-0016, NFL-0017

## Canonical sources

- [Architecture Overview](../../architecture/overview.md#initialize-or-resume)
- [MVP Specification](../../product/mvp-spec.md#primary-user-journey)

## Outcome

Neutral league and initial-snapshot observations create or resume one internal draft with validated configuration, resolved identities, pinned versions, and committed canonical state.

## Scope

Implement application operations behind `POST /v1/leagues`, `POST /v1/drafts`, and `GET /v1/drafts/{draft_id}`; creation returns stable internal IDs rather than reusing provider identifiers.

## Acceptance criteria

- [x] The canonical MVP-supported 8-team snake configuration initializes with validated order,
  user team/slot, roster rules, and one pinned data/model set. (The ticket's 10/12 wording was
  superseded by the canonical MVP supported matrix.)
- [x] Repeated initialization resumes the matching draft rather than duplicating it.
- [x] Unsupported rules, unknown identities, and conflicts produce visible blocked/degraded outcomes while preserving valid state.
- [x] Canonical state commits before any recommendation calculation.

## Validation

- [x] `test_draft_service.py` covers supported initialization, repeat/resume, incompatible format,
  unresolved identity, conflicts, and restart persistence.
- [x] Provider/external pairs are stored separately from generated `league_*`/`draft_*` internal IDs.

## Completion summary

Implemented neutral league registration and draft initialization/resume under `/v1/leagues` and
`/v1/drafts`, with immutable pin/config conflict handling and no provider ID reuse as primary IDs.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
