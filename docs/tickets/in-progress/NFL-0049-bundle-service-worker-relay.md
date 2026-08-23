# NFL-0049 — Bundle the service-worker relay

- Status: In progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0047, NFL-0048

## Canonical sources

- [Architecture overview — Extension](../../architecture/overview.md#extension)
- [Development guide — Toolchain status](../../engineering/development.md#toolchain-status)
- [Threat model — Required controls](../../security/threat-model.md#required-controls)

## Outcome

The Manifest V3 service worker reliably registers the local-backend message relay in the unpacked
extension without relying on a browser module import chain.

## Context

The content script renders, while direct service-worker authenticated diagnostics are healthy, but
the live panel continues to report a disconnected backend. Bundling the worker alongside the
already-bundled content script makes the manifest-declared execution boundary self-contained and
removes module loading as a possible relay failure.

## In scope

- Emit a classic bundled service-worker entrypoint.
- Keep the manifest worker declaration and build checks aligned.
- Verify the supported Sleeper page can proceed past the backend health gate.

## Out of scope

- Changes to pairing storage, backend authentication, Sleeper API requests, or draft logic.

## Acceptance criteria

- [ ] The built service worker contains no static module syntax and is declared as a classic worker.
- [ ] Existing extension checks pass.
- [ ] Live reload reaches the next Sleeper initialization state rather than a disconnected health gate.

## Validation

- [ ] Record each applicable check and its result.

## Completion summary

Complete when closing the ticket, including the evidence supporting `Resolution: Done`.

## History

- 2026-08-23 — Created in progress after direct authenticated diagnostics succeeded but the content-panel relay still rendered backend disconnected.
