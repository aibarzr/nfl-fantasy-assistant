# NFL-0030 — Implement ESPN league configuration and initial-snapshot adapter

- Status: Blocked
- Resolution: Unresolved
- Phase: 5 — ESPN live loop
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0006, NFL-0022, NFL-0029

## Canonical sources

- [Architecture Overview](../../architecture/overview.md#initialize-or-resume)
- [Extension–Backend Protocol](../../contracts/protocol.md#neutral-references-and-observations)

## Outcome

The ESPN adapter converts supported league configuration, draft order, user identity, player references, and ordered picks into neutral v1 initialization/snapshot messages.

## Scope

Implement the validated structured/browser/DOM fallback chain against sanitized fixtures. Derived round, roster, availability, and scoring outputs remain backend responsibilities.

## Acceptance criteria

- [ ] The supported 8-team fixture serializes exact neutral contract types; non-8-team fixtures reject visibly.
- [ ] Snapshot scope and completeness are explicit and never inferred from a virtualized list.
- [ ] Unsupported league rules and incomplete/ambiguous extraction are visible and do not submit trusted state.
- [ ] Platform objects and selectors remain confined to the ESPN adapter.

## Validation

- [ ] Test structured, browser-state, DOM-fallback, partial, incompatible, and unsupported fixtures offline.
- [ ] Run contract serialization checks against generated TypeScript/OpenAPI types.

## Progress before blocker

Implemented the structured ESPN adapter boundary. It validates the 8-team snake order, carries an
explicit `configuration_and_scheduled_order` / incomplete scope, returns the stable unavailable
outcomes for browser-state and DOM sources, and serializes the generated `DraftCreateRequest` only
when independently verified user identity and semantic codebook context are supplied. Offline tests
exercise the committed 8-team fixture, unsupported size/order, all source paths, missing identity
or codebook, contradictory user/semantic context, and checked contract serialization.

## Blocker

The canonical league-extraction finding still establishes neither the active user's team/slot nor
the semantic roster/scoring codebook. The observed numeric ESPN codes cannot be interpreted as
`LeagueConfig`, and selecting a team from the URL, order, display text, or roster would violate the
identity and configuration rules.

Impact: trusted draft initialization cannot occur, so NFL-0031, NFL-0034, NFL-0035, and NFL-0036
cannot complete their live-loop acceptance work.

Unblock condition: supply a sanitized browser-visible source linking the active user to one team
and slot, plus an authorized, versioned codebook covering every nonzero supported roster and
scoring code. The fixture may then serialize a trusted neutral initialization request.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Corrected fixture scope to the canonical 8-team MVP; the prior 10/12-team wording was not authoritative.
- 2026-07-31 — Started by Codex after NFL-0029 completed.
- 2026-07-31 — Blocked after implementing safe structured parsing; user identity and semantic codebook evidence remain unavailable.
- 2026-07-31 — Extended adversarial offline coverage; every incomplete or contradictory context remains unavailable.
