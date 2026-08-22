# NFL-0022 — Finalize Pydantic/OpenAPI v1 contracts and checked TypeScript types

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0002, NFL-0017, NFL-0018, NFL-0019, NFL-0020, NFL-0021

## Canonical sources

- [Extension–Backend Protocol](../../contracts/protocol.md#scope-and-ownership)
- [Extension–Backend Protocol](../../contracts/protocol.md#compatibility)

## Outcome

Backend Pydantic models and generated OpenAPI become the exact v1 HTTP authority, with generated or mechanically checked TypeScript consumers.

## Scope

Finalize schemas for documented resources, neutral observations, state/recommendation status, errors, authentication, revisions, versions, and compatibility; add repeatable contract generation/drift checks.

## Acceptance criteria

- [x] Wire names, timestamps, IDs, enums, errors, authentication, and HTTP status semantics match the protocol.
- [x] Platform-specific and backend-derived facts do not leak into neutral input models.
- [x] TypeScript request/response types are generated from OpenAPI and are not hand-maintained duplicates.
- [x] Compatibility/error cases and generated drift are covered by tests.

## Validation

- [x] `generate_openapi.py` produces `backend/openapi.json` and generated TypeScript types;
  `check-openapi-contract.sh` regenerates into temporary paths and rejects drift.
- [x] API tests cover valid, malformed, unauthorized, conflict, and unavailable responses;
  extension typecheck/build verifies generated consumers on 2026-07-30.

## Completion summary

Pydantic/FastAPI is the exact v1 authority. Generated OpenAPI and TypeScript request/response
types are checked by the repository quality workflow.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
