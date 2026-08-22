# NFL-0006 — Validate league settings, draft order, and user-slot extraction

- Status: Done
- Resolution: Done
- Phase: 1 — Technical spikes
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0005

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#supported-matrix)
- [Domain Model](../../domain/domain-model.md#leagueconfig)
- [Extension–Backend Protocol](../../contracts/protocol.md#neutral-references-and-observations)

## Outcome

Evidence distinguishes the ESPN facts that can be normalized without guessing from configuration
facts that must currently produce an explicit unsupported outcome.

## Scope

Validate the supported 8-team snake configuration, roster slots, scoring, flex/superflex/TE-premium representation, draft order, and user identity; document visible rejection behavior for unsupported rules.

## Acceptance criteria

- [x] Each required neutral field is mapped to a stable observed source or an explicit unsupported outcome.
- [x] Team count, order, user slot, roster slots, and scoring can be checked against sanitized examples.
- [x] Surface and league provider remain distinct concepts.
- [x] No derived backend fact is proposed as authoritative browser input.

## Validation

- [x] Exercised the representative 8-team sanitized case and the synthetic unsupported 10-team configuration.
- [x] Recorded the user-slot and numeric-code ambiguity and clarified the canonical protocol before implementation.

## Completion summary

[`ESPN league extraction finding — 2026-07-30`](../../espn-data/league-extraction-finding-2026-07-30.md)
validates the 8-team snake order/configuration shape and the unsupported 10-team outcome. It also
records three deliberately non-guessed gaps: a user slot, roster-code semantics, and scoring-code
semantics. The protocol now requires an explicit unavailable outcome when user team/slot cannot be
observed together, and a versioned adapter codebook before provider numeric codes become domain
configuration.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex after NFL-0005 completed.
- 2026-07-30 — Completed by Codex with explicit unsupported outcomes for unobserved semantics.
