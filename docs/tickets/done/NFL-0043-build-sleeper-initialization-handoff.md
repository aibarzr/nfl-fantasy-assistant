# NFL-0043 — Build Sleeper initialization handoff

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0018, NFL-0037, NFL-0039, NFL-0040, NFL-0041, NFL-0042

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#primary-user-journey)
- [Architecture Overview](../../architecture/overview.md#extension)
- [Protocol](../../contracts/protocol.md#neutral-references-and-observations)
- [Data and Player Identity](../../data/data-and-identity.md#identity-resolution)
- [ADR-0002](../../architecture/decisions/0002-extension-bound-provider-api-access.md)
- [Sleeper observability finding](../../sleeper-data/observability-finding-2026-08-22.md)
- [Development Guide](../../engineering/development.md#quality-gates)

## Outcome

The Sleeper service-worker adapter can construct and submit a strictly validated, neutral
league-and-draft initialization request from the documented draft, league, roster, user, and picks
responses, or stop before a backend mutation with an actionable stable error.

## Context

NFL-0037 established the documented user-to-roster-to-slot route and complete-picks semantics.
NFL-0039 and NFL-0042 have published the local exact crosswalk and prepared-pool coverage needed
to make identity a valid release gate. The runtime must still never treat a page URL, display name,
or browser authentication as a user identity, and must retain neither raw provider payloads nor
private provider identifiers.

## In scope

- Store only explicit, opaque local initialization context in extension storage: Sleeper user ID and
  pinned dataset, feature, and model versions.
- Validate the exact active draft, its league-backed neutral configuration, unique configured-user
  membership/roster/slot relationship, complete 8-team snake order, and initial pick snapshot.
- Use the service worker alone for documented API reads and for neutral loopback league/draft
  submission; make initialization safe to retry after a worker or page restart.
- Render an actionable non-current result whenever local context or any provider fact is missing,
  malformed, cross-scoped, ambiguous, unsupported, or inconsistent.
- Cover the happy path and material safe stops with synthetic fixtures and unit tests.

## Out of scope

- Runtime import of the local prepared dataset/crosswalk into the backend, recommendation
  generation, polling, or live-pick observation after initialization.
- Inferring the signed-in Sleeper account from a page, username, display name, creator metadata,
  cookie, or browser authentication material.
- Any backend-to-Sleeper request, provider write, real payload retention, or changes to ESPN.

## Acceptance criteria

- [x] The adapter validates the documented provider facts and emits only neutral protocol data.
- [x] A configured opaque user ID resolves to exactly one same-league roster and draft slot; all
  other identity states visibly reject before a backend mutation.
- [x] League and draft initialization is idempotently handed to the paired loopback backend only
  after all gates, including the initial complete pick snapshot, pass.
- [x] Restart-safe local extension context pins dataset, feature, and model versions without
  exposing tokens or private provider data to a page.
- [x] Tests and documentation demonstrate the request surface, ordering, failure behavior, and
  sanitization limits; no live network request occurs in CI.

## Validation

- [x] Run applicable extension format, lint, type, test, and build checks.
- [x] Run the backend/OpenAPI and documentation checks affected by the wire consumer.
- [x] Confirm no private provider identifiers, raw responses, or generated artifacts are committed.

## Blocker

None.

## Completion summary

Implemented `sleeper_initialize` as a service-worker-only operation. It first requires ready local
data, identity, and recommendation diagnostics, then loads only per-device opaque user/version
context from extension storage. The adapter validates draft/league scope, translated roster and
scoring configuration, user membership, exactly one owned roster, slot-map/draft-order agreement,
full snake order, and the complete initial pick snapshot before submitting neutral league/draft
requests to the paired backend. The backend draft endpoint remains safely retryable by provider
draft identity. No raw provider response or private identifier is retained.

`./scripts/quality.sh all` completed backend (99 tests), extension (50 tests), build, OpenAPI, and
documentation checks. Its final tracked-drift check correctly failed because this active worktree
contains this uncommitted implementation and the preceding approved data/scoring changes; no
generated output or sensitive local data was added. `git diff --check` passed.

## History

- 2026-08-23 — Created and started after the prepared-pool crosswalk publication. Separates the
  adapter’s verified initialization handoff from runtime data activation, polling, and full
  end-to-end live-draft acceptance.
- 2026-08-23 — Completed with synthetic adapter/service-worker coverage for valid initialization,
  roster/slot and scope mismatches, allowed API request surface, non-ready local-runtime safe stop,
  and neutral loopback submission. Runtime data activation and live-loop acceptance remain separate.
