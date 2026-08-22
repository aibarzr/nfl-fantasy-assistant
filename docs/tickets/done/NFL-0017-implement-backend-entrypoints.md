# NFL-0017 — Implement configuration, authentication, health, and diagnostics API

- Status: Done
- Resolution: Done
- Phase: 3 — Backend draft core
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-30
- Depends on: NFL-0004, NFL-0016

## Canonical sources

- [Extension–Backend Protocol](../../contracts/protocol.md#resources)
- [Local Security Threat Model](../../security/threat-model.md#required-controls)
- [Operations Runbook](../../operations/runbook.md#diagnostics-and-logs)

## Outcome

A loopback-only FastAPI entrypoint validates configuration, exposes minimal unauthenticated health, and protects actionable diagnostics with the paired bearer token.

## Scope

Implement startup validation, `GET /v1/health`, authenticated `GET /v1/diagnostics`, narrow CORS/origin handling, correlation IDs, stable error envelopes, and redacted structured logs.

## Acceptance criteria

- [x] The default bind is `127.0.0.1` and never broadens silently.
- [x] Every endpoint except health requires valid bearer authentication and an allowed origin/context.
- [x] Health reveals no sensitive state; diagnostics distinguish database, data/model, identity, adapter, and recommendation readiness.
- [x] Errors use protocol status/code semantics and state is not mutated on validation or security failure.

## Validation

- [x] `test_api.py` and `test_pairing.py` cover missing/invalid credentials, disallowed origin,
  malformed runtime configuration, validation failures, and unavailable recommendations.
- [x] API tests assert health/error responses do not contain tokens; diagnostics contains only
  component readiness. Full quality checks passed on 2026-07-30.

## Completion summary

Implemented the loopback FastAPI app, bearer/origin controls, CORS, correlation IDs, stable error
envelopes, safe runtime configuration, diagnostics, and the `serve` CLI command.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-30 — Started and completed by Codex.
