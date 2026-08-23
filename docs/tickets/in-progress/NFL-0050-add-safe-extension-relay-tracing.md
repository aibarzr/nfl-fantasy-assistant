# NFL-0050 — Add safe extension relay tracing

- Status: In progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0049

## Canonical sources

- [Architecture overview — Extension](../../architecture/overview.md#extension)
- [Threat model — Required controls](../../security/threat-model.md#required-controls)

## Outcome

The extension emits bounded console traces that identify the lifecycle/relay operation and success
or error category without logging tokens, URLs, draft IDs, or provider payloads.

## Context

Direct worker fetches prove the backend is healthy, but the live panel remains non-current. Safe
local traces are required to identify whether the failure occurs in the content lifecycle, worker
relay, or later initialization path.

## In scope

- Emit safe console traces for initialization lifecycle and worker relay outcomes.
- Suppress successful five-second synchronization trace noise.
- Validate and document the absence of sensitive trace fields.

## Out of scope

- Persistent telemetry, remote logging, provider payload logging, or browser automation.

## Acceptance criteria

- [ ] A page refresh exposes content and worker outcome traces for health and initialization.
- [ ] Successful polling does not create repetitive console noise.
- [ ] Trace output contains no credentials or provider/draft identifiers.

## Validation

- [ ] Record each applicable check and its result.

## Completion summary

Complete when closing the ticket, including the evidence supporting `Resolution: Done`.

## History

- 2026-08-23 — Created in progress after manual service-worker diagnostics succeeded while the live panel remained disconnected.
