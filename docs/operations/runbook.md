# Local Operations Runbook

## Current limitation

The backend draft core and deterministic recommendation engine are implemented. The ESPN live
adapter remains blocked on validated initialization/recovery evidence. Sleeper is approved for a
read-only discovery spike only and must not be used for a live draft until its adapter, identity
mapping, recovery evidence, and end-to-end acceptance fixture are complete. Neutral K/DEF
domain-data-model support is complete.

## Installation and startup checklist

The supported local startup procedure is:

1. Run `uv --directory backend sync --all-groups --frozen` and `npm --prefix extension ci`.
2. Generate a locally stored token with `uv --directory backend run python -m nfl_fantasy_assistant pair init --config-dir <config-dir>`.
3. Pair that one-time token in extension service-worker developer tools using the documented
   `chrome.storage.local` command in the development guide. Never use a page console.
4. Add the exact installed extension origin and safe SQLite filename to the private `config.toml`
   `[runtime]` section; see `backend/config.example.toml`.
5. Run `./scripts/quality.sh all`, then start the loopback service with
   `uv --directory backend run python -m nfl_fantasy_assistant serve --config-dir <config-dir>`.
6. Load `extension/dist` unpacked only after the relevant provider adapter has passed its release
   checks; an unsupported or discovery-only provider must display a non-current state.

`GET /v1/health` confirms liveness without credentials. Use authenticated `GET /v1/diagnostics`
from the extension context to identify database, data/model, identity, adapter, and recommendation
readiness. The backend rejects non-loopback configuration, missing/invalid tokens, and origins
other than the configured extension origin.

## Pre-draft readiness

- Backend health and authenticated diagnostics are green.
- League format and user draft slot match the platform.
- Every configured position, including K and DEF where present, has a supported identity route,
  prepared-value coverage, and versioned scoring translation.
- Dataset and market-source timestamps meet configured freshness policy.
- Model/data versions are pinned for the session.
- Initial snapshot pick count, order, rosters, and unresolved-player count are visible.
- Provider API freshness, rate-limit/backoff state, and complete-snapshot status are green when a
  provider adapter uses a documented structured API.
- Recommendation fixture/smoke check completes within the performance budget.
- There is sufficient local disk space and the SQLite database is writable.

Do not proceed with trusted recommendations while configuration, identity, or reconciliation is blocked.

## Recovery procedures

### Extension or page reload

Reload/reopen the supported page. The extension must reconnect, fetch or submit a complete-enough snapshot, and resume the existing internal draft ID. Confirm canonical pick count and current recommendation revision before relying on it.

For a Sleeper adapter, the service worker must obtain a fresh validated API snapshot after reload;
it must not recover from a cached page DOM or an unverified local pick list.

### Backend restart

Restart using the documented command, verify readiness and pinned versions, then let the extension reconcile. Do not create a second draft merely because the process restarted.

### Missed pick or count mismatch

Capture current diagnostics, request a fresh platform snapshot, and reconcile. If the conflict is unambiguous and supported, canonical state is rebuilt atomically from accepted history plus missing picks. Otherwise retain state, enter blocked/reconciling status, and do not manually edit SQLite.

### Unknown player

Record provider/external ID, sanitized display hints, source surface, pick, and diagnostics. Refresh/repair the identity mapping through the supported data workflow, preserving provenance. Do not guess by name or remove a likely candidate manually.

### Platform adapter failure

Stop accepting observations from the incompatible adapter, capture sanitized HTML/structured-response evidence, record browser/surface/date, and reproduce against a fixture. Existing canonical state remains valid but recommendations are marked stale until reconciliation succeeds.

### Stale or failed data refresh

Keep the last fully validated published dataset. A failed build never replaces it. New draft sessions may use the old version only if freshness policy allows and the UI shows the warning; active sessions do not switch versions silently.

## Diagnostics and logs

Authenticated diagnostics should report API compatibility, database readiness, active draft/revision, adapter observation time, unresolved/conflict counts, dataset/model/feature versions, source freshness, and last recommendation latency.

Structured logs should correlate `request_id`, `league_id`, `draft_id`, `event_id`, surface/provider, action, player/pick when resolved, status, and model version. Never request or share tokens, cookies, raw personal payloads, or unsanitized captures during diagnosis.

## Backup, export, and reset

Before material upgrades, copy the SQLite database and the active dataset/model manifests using the future documented backup command. Exported diagnostic/replay bundles exclude credentials and redact platform/user identifiers by default.

Reset must target one explicitly identified draft/session or the application data directory shown to the user, require confirmation, and report what is recoverable. Never instruct users to recursively delete broad home/workspace paths.

## Release and rollback

Each distributed build records application, API, database schema, extension, model, feature, and dataset compatibility versions. Upgrade procedures run tested forward migrations and retain a backup. Rollback uses a release known to support the current schema or restores the matching backup; it never edits applied migrations.

Extension packaging verifies manifest permissions and contains no tokens or real fixtures. Release notes identify protocol, migration, data/model, permission, and operator-action changes.
