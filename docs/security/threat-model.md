# Local Security Threat Model

## Scope

The MVP consists of an extension running on third-party pages and a backend listening on the user's machine. “Local” is not equivalent to trusted: arbitrary websites and other local processes may attempt to call loopback services, while page scripts must not gain the backend token through the DOM/content-script boundary.

## Assets

- Shared backend token and any source credentials.
- League configuration, draft history, rosters, and local databases.
- Integrity of canonical state and recommendations.
- Captured platform responses/fixtures and logs.
- Provider user, league, roster, draft, individual-player, and team-defense identifiers observed from Sleeper.
- Extension permissions and update/package integrity.

## Trust boundaries

- Third-party page JavaScript is untrusted.
- Content scripts operate in an isolated world but must validate messages and avoid exposing secrets to page context.
- The extension service worker is trusted to hold machine-local configuration and call the backend.
- Loopback callers are unauthenticated until the backend validates the bearer token. Browser-origin
  requests are additionally restricted to the configured extension origin; Chromium extension
  service-worker fetches may omit `Origin` and remain token-authenticated.
- External datasets and dependencies are untrusted inputs until validated.
- A documented provider API is an untrusted external input even when it requires no credential.

## Required controls

- Bind only to `127.0.0.1` by default; startup must not silently broaden the interface.
- Require a high-entropy bearer token for all non-health operations.
- Store the token in extension storage inaccessible to page scripts and in a permission-restricted backend configuration location; never put it in URLs, DOM, logs, fixtures, or source.
- Define a narrow CORS policy for the installed extension origin. Do not use wildcard origins with
  authenticated endpoints. Reject a present `Origin` that differs from that extension; permit an
  omitted `Origin` only through bearer authentication because Chromium extension service workers
  may omit it.
- Validate content-script/service-worker message origin, shape, supported surface, size, and operation.
- Grant only required host permissions for supported domains and loopback; prefer optional permissions when feasible.
- A provider API request originates only from the extension service worker after exact-surface
  activation and validated local configuration. It uses a narrowly scoped host permission, bounded
  polling, backoff, and response-size/schema validation; content scripts do not fetch it directly.
- Validate all external IDs, lengths, enums, numeric ranges, snapshots, and event ordering server-side.
- Use parameterized database access and safe file paths rooted in configured data directories.
- Redact authorization, cookies, credentials, personal/account identifiers, and sensitive payloads from logs and diagnostics. Local extension console traces may record only operation names and outcome categories; they must not record tokens, URLs, draft IDs, or provider payloads.
- Pin dependencies through lockfiles, review new dependencies/permissions, and build release artifacts reproducibly.

## Token lifecycle

Scaffolding must choose and document an installation/pairing mechanism before enabling authenticated integration. It must generate the token locally using a cryptographically secure source, avoid manual embedding in the extension bundle, support rotation/revocation, and make a mismatched token diagnosable without revealing it.

Rotation invalidates the old token and requires explicit extension re-pairing. Backend backup/export excludes tokens by default.

## Threat scenarios

| Threat | Required response |
|---|---|
| Malicious website calls loopback | Exact-origin CORS where an origin is sent, bearer authentication for every non-health operation, and no sensitive unauthenticated response |
| Page tries to read token | Token remains in service-worker storage/context and never crosses into page DOM/messages |
| Forged/oversized observation | Schema, size, surface/provider and domain validation; reject without state mutation |
| Replay of a valid event | Idempotency returns the established result |
| Event ID reused with changed payload | Return conflict and log correlation, preserving state |
| Poisoned mapping/source data | Validate provenance/uniqueness, quarantine conflict, pin last valid version |
| Provider API unavailable, throttled, or malformed | Stop fresh observations, retain canonical history, render a non-current state, and retry from a five-second base interval with capped exponential backoff (maximum sixty seconds) |
| Extension fetches an unapproved host or page script requests provider data | Exact content-script matching, minimal host permissions, service-worker-only request path, and message validation |
| Logs or fixtures expose user data | Structured redaction and fixture sanitization gates |
| Compromised dependency | Lockfiles, minimal dependencies, review/update process and reproducible rebuild |

## Privacy and retention

Store only data needed for recommendations, reproducibility, and diagnostics. Keep it local by
default and provide documented deletion/reset and export behavior. Provider user, league, roster,
and draft identifiers are private local configuration/diagnostic values and are redacted from
exports, fixtures, and logs. Remote telemetry is off-scope and cannot be introduced without
explicit consent, a data inventory, retention policy, and updated threat model.

The approved current player-status overlay stores only exact mapped provider IDs, neutral status,
observation/receipt timestamps, source revision, checksum, and freshness state. It excludes raw
catalog payloads, player display names, medical notes, and browser-authentication material. A
missing or stale overlay is represented as `unknown`, never as a healthy observation.

## Security acceptance

Before live integration, test unauthorized requests, disallowed origins, token rotation, malformed/large payloads, message-source validation, log redaction, and minimal manifest permissions. Security failures must never partially mutate canonical state.
