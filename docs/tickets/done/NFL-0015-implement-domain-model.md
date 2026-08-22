# NFL-0015 — Implement framework-independent domain entities and invariants

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0001

## Canonical sources

- [Domain Model](../../domain/domain-model.md#core-entities)
- [Architecture Overview](../../architecture/overview.md#dependency-direction)

## Outcome

Pure internal domain models express league, draft, pick, roster, player, recommendation, identity, and reconciliation invariants independently of frameworks and storage.

## Scope

Implement explicit internal types, lifecycle states, validation outcomes, and pure transition rules. Transport, SQLite, Polars/nflreadpy, and browser types stay outside this boundary.

## Acceptance criteria

- [x] `LeagueConfig`, `DraftSession`, `DraftPick`, `TeamRoster`, `Player`, and `RecommendationSnapshot` semantics are represented.
- [x] Unique event/pick/player, draft-order, immutable-config, pinned-version, roster, and availability invariants are enforced.
- [x] Blocked/reconciling states preserve valid history and prevent untrusted recommendations.
- [x] Domain modules import no FastAPI, SQLite, Polars/nflreadpy, or platform-specific types.

## Validation

- [x] `test_draft_domain.py` covers transitions, gaps, uniqueness, roster legality, and availability; `test_domain_import_boundary.py` AST-checks prohibited dependencies.
- [x] Backend format, lint, typecheck, test, build, contract, extension, and docs checks passed on 2026-07-30.

## Completion summary

Implemented immutable standard-library domain entities and pure transitions in `domain/draft.py`.
Blocked/reconciling state retains accepted history and the API refuses non-current recommendations.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started by Codex.
- 2026-07-30 — Completed by Codex.
