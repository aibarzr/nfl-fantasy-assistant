# NFL-0032 — Implement resilient service worker and authenticated API client

- Status: Done
- Resolution: Done
- Phase: 5 — ESPN live loop
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0004, NFL-0022

## Canonical sources

- [Architecture Overview](../../architecture/overview.md#extension)
- [MVP Specification](../../product/mvp-spec.md#degraded-and-failure-behavior)

## Outcome

The service worker securely relays neutral v1 requests, survives suspension/reload, and reports connection/authentication/compatibility failures without owning canonical state.

## Scope

Implement generated/checked API client use, token storage and bearer injection in trusted context, retries for safe operations, correlation IDs, compatibility checks, and explicit connection state.

## Acceptance criteria

- [x] Token material never crosses into page DOM or page-facing messages.
- [x] Worker restart resumes via backend state and fresh snapshot rather than irreplaceable memory.
- [x] Retry behavior respects idempotency and distinguishes unauthorized, incompatible, unavailable, and conflict responses.
- [x] Client serialization uses the checked contract types and configured loopback endpoint.

## Validation

- [x] `api-client.test.ts` covers unavailable/retry, unauthorized, and incompatible responses; safe reads and idempotent event submission alone retry.
- [x] `service-worker.test.ts` proves fresh configuration loading across requests (including token rotation), suspension-safe stateless handling, and secret-free worker errors.
- [x] The worker exposes only typed neutral response data and never serializes its stored pairing configuration into a message or log.

## Completion summary

Implemented a service-worker-only authenticated v1 client using generated contract types, bounded
requests, explicit connection error states, and safe retries. The worker reloads paired
configuration for every relay request so rotation, suspension, and reload preserve no canonical or
secret in-memory state.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex.
- 2026-07-31 — Completed by Codex.
