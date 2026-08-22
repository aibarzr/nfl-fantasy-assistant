# ADR-0002: Keep provider API access inside extension adapters

- Status: Accepted
- Date: 2026-08-22
- Supersedes: none

## Context

Sleeper provides a documented read-only API that can expose structured draft configuration, order,
and picks more reliably than a rendered draft-board DOM. The project must support a private,
8-team NFL snake redraft without moving platform-specific behavior or canonical draft state into
the wrong layer.

The architecture assigns platform-specific behavior to extension adapters and assigns canonical
state, player identity, recommendation logic, persistence, and local authentication to the
backend. Having the backend poll Sleeper directly would change that established system boundary.

## Decision

The Sleeper extension adapter owns exact-surface activation and documented Sleeper API access. Its
service worker, not a content script, may make the narrowly permitted structured requests after
validated local configuration. It normalizes validated facts into the existing neutral protocol
and submits them to the paired loopback backend.

The backend continues to own canonical state, idempotency, reconciliation, provider-to-internal
identity resolution, recommendation computation, provenance, and SQLite persistence. It does not
call Sleeper directly. Browser authentication material is never read, copied, or stored; no
Sleeper API token is introduced.

## Consequences

- Sleeper API host permissions, request cadence, backoff, response validation, and sanitization
  belong to the extension adapter and require dedicated tests.
- The adapter needs verified local user/draft configuration and must not infer an active identity
  from names, URLs, or partial page state.
- A complete API pick list may support reconciliation only after discovery proves its ordering and
  completeness semantics.
- The neutral backend protocol and generated clients require an additive Sleeper-provider update.
- The external API becomes a documented source/trust boundary, but not an offline model-data input.

## Alternatives considered

### Backend polls Sleeper directly

Rejected. It places platform-specific remote access in the backend, contradicting the established
extension-adapter boundary and enlarging the backend's external network trust boundary.

### Parse the Sleeper page DOM only

Rejected. A rendered or virtualized draft board cannot establish a complete recovery snapshot
without separate evidence, whereas the documented structured API may do so after validation.

### Remove the local backend

Rejected. The provider API does not supply the project's canonical state, identity mapping,
versioned prepared player values, deterministic recommendation logic, provenance, or local
pairing/security controls.
