# NFL-0051 — Bind worker fetch to the service-worker global

- Status: In progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0050

## Canonical sources

- [Architecture overview — Extension](../../architecture/overview.md#extension)
- [Development guide — Extension tests](../../engineering/development.md#extension)

## Outcome

The local API client invokes the native browser transport with the service-worker global receiver,
so a content-script relay can make the same loopback call that succeeds from worker DevTools.

## Context

Live traces proved the content-to-worker relay receives a health request and direct worker
`fetch(...)` succeeds. The client retained native `fetch` on an object and invoked it as a method,
which changes its receiver from the service-worker global to the client instance.

## In scope

- Invoke the configured transport with `globalThis` as its receiver.
- Add a regression test for that receiver.
- Validate the live extension reaches the next initialization gate.

## Out of scope

- Changing API endpoints, pairing, CORS, draft logic, or the polling cadence.

## Acceptance criteria

- [ ] The API client invokes its transport with the service-worker global receiver.
- [ ] The extension build and test suite pass.
- [ ] A refreshed Sleeper page passes the local backend health gate.

## Validation

- [ ] Record each applicable check and its result.

## Completion summary

Complete when closing the ticket, including the evidence supporting `Resolution: Done`.

## History

- 2026-08-23 — Created in progress after relay tracing showed worker health failed while identical direct service-worker fetches succeeded.
