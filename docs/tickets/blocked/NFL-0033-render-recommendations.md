# NFL-0033 — Render status, freshness, and explainable recommendations

- Status: Blocked
- Resolution: Unresolved
- Phase: 5 — ESPN live loop
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0027, NFL-0032

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#primary-user-journey)
- [Recommendation Engine](../../modeling/recommendation-engine.md#output-and-explanation)

## Outcome

The active ESPN page displays current Top-N recommendations, confidence, components, reasons, freshness/provenance, and actionable degraded status without automating selections.

## Scope

Implement an isolated extension UI for connection, authorization, adapter, identity, reconciliation, data/model, latency, and recommendation state. It renders backend decisions and contains no fantasy strategy.

## Acceptance criteria

- [ ] Each candidate shows rank, score, confidence, measured reasons/components, relevant warnings, and model/feature/dataset versions.
- [ ] Stale, blocked, unresolved, incompatible, unauthorized, and disconnected states cannot appear current.
- [ ] UI updates are recoverable across page and worker reloads and do not interfere with ESPN interaction.
- [ ] No control automates or submits a fantasy pick.

## Validation

- [ ] Test current, loading, empty, stale, blocked, error, reload, and long-content states.
- [ ] Verify accessibility, supported Chromium rendering, and absence of horizontal overflow or page breakage.

## Progress before blocker

Implemented a shadow-DOM, read-only draft-board panel and a page renderer that asks the
service-worker for a fresh backend recommendation response after each reload. It renders measured
components, confidence, reason codes/text, warnings, pinned provenance, and non-current status;
unit tests cover current, loading, empty, stale, blocked, error, long-content, escaping, and
absence-of-pick-control states. The content script now mounts that panel only on the exact confirmed
ESPN path, checks worker/backend readiness, and renders a non-current initialization state after a
page or worker reload. The neutral contract carries persisted candidate warnings so the UI does not
invent freshness messaging.

## Blocker

NFL-0029 is complete, and the panel now mounts only on its exact confirmed surface. However,
`renderRecommendations` requires a canonical `draft_id`; NFL-0030 correctly cannot create one
until the active user team/slot and semantic roster/scoring codebook are observed. Treating any
URL/team hint as a draft identity would expose a current-looking result without canonical state.

Impact: current recommendation rendering and active-page Chromium accessibility/non-interference
validation cannot complete; NFL-0035 cannot prove the end-to-end loop.

Unblock condition: satisfy NFL-0030 with the documented sanitized identity and codebook evidence,
then initialize a draft and use its backend-issued ID to exercise current and recovery rendering.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Blocked pending NFL-0029; the reusable read-only UI was retained without guessing an ESPN activation rule.
- 2026-07-31 — Extended offline state coverage while blocked; active-page validation remains unavailable without NFL-0029 evidence.
- 2026-07-31 — Reopened by Codex after NFL-0029 completed; content-script lifecycle integration can now proceed.
- 2026-07-31 — Blocked after exact-surface lifecycle integration; a canonical draft ID remains unavailable pending NFL-0030 evidence.
