# NFL-0048 — Accept originless extension-worker requests

- Status: In progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0047

## Canonical sources

- [Architecture overview — Extension](../../architecture/overview.md#extension)
- [Threat model — Required controls](../../security/threat-model.md#required-controls)

## Outcome

The authenticated loopback API accepts a Chromium extension service-worker request when Chromium
omits its `Origin` header, while continuing to reject any present origin other than the configured
extension origin.

## Context

Live validation showed that the configured extension service worker reaches loopback but its
authenticated request carries no usable `Origin` header. The bearer token remains mandatory;
origin validation must not prevent that documented extension transport from operating.

## In scope

- Permit originless, bearer-authenticated requests.
- Preserve rejection of a mismatched present origin and the exact CORS allowlist.
- Cover both paths with API tests and document the control.

## Out of scope

- Relaxing bearer authentication, loopback binding, CORS allowlists, or extension permissions.

## Acceptance criteria

- [ ] An originless request with a valid bearer token reaches an authenticated endpoint.
- [ ] A mismatched present origin remains rejected before any state mutation.
- [ ] Relevant security documentation and API tests pass.

## Validation

- [ ] Record each applicable check and its result.

## Completion summary

Complete when closing the ticket, including the evidence supporting `Resolution: Done`.

## History

- 2026-08-23 — Created in progress after the configured Chromium extension service worker received a `403 disallowed_origin` response on authenticated diagnostics.
