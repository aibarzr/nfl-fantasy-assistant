# ADR-0001: Store local bearer tokens separately in backend and extension private storage

- Status: Accepted
- Date: 2026-07-29

## Context

The extension and loopback backend require a high-entropy bearer token, but third-party page
scripts must never access it. Phase 0 needs a pairing and lifecycle mechanism before authenticated
integration exists.

## Decision

The backend generates a 256-bit URL-safe token using Python's operating-system-backed CSPRNG. It
stores it in `backend.token` under the user-private configuration directory (mode `0700` directory,
mode `0600` file). The token is deliberately excluded from backup/export APIs and from version
control. Initialization and rotation print the new value once to the operator; errors refer only to
pairing state, never the token.

The extension validates a loopback HTTP URL and token shape, then stores the pair only in
`chrome.storage.local`, reachable from extension contexts but not page JavaScript. The current
scaffold has no options-page token field because passing a token through a DOM would violate the
threat model. During scaffolding, the operator pairs from the extension service-worker developer
tools console; a future dedicated extension-context pairing surface may replace that procedure
only if it keeps the token out of page/DOM contexts.

Rotation replaces the backend token atomically and invalidates the old extension configuration.
Revocation deletes the backend token; subsequent authenticated use must fail visibly until a new
token is generated and paired. Runtime bearer enforcement and CORS are deferred to NFL-0017.

## Consequences

- The token never appears in URLs, source, bundles, page DOM, fixtures, or application logs.
- A missing or malformed token is diagnosable without revealing credentials.
- Operators must explicitly re-pair after rotation or revocation.
- Backup and export tooling must retain this default exclusion.

## Rejected alternatives

- Embedding a token in the extension manifest/bundle or a tracked configuration file exposes it to
  source control and package inspection.
- Passing a token through content-script/page messages or a page DOM form crosses the untrusted
  page boundary.
- A localhost endpoint that dispenses tokens would add an unauthenticated secret-distribution
  service before its authentication and CORS controls exist.
