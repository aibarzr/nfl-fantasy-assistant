# Sanitized Sleeper Discovery Evidence

This directory contains the narrow, sanitized evidence from the authorized private mock/test-draft
investigation for NFL-0037. It contains no real user, league, draft, roster, player, or team
identifiers; no URLs; and no request/response headers, cookies, credentials, or raw payloads.

The underlying browser/API observations are local-only. The committed JSON files are deliberately
synthetic validation inputs that preserve only the documented field shape, state transitions, and
safe-stop cases needed for offline adapter tests. They are not a database of Sleeper data and are
not a runtime asset.

`node scripts/check_sleeper_spike_fixtures.mjs` validates the fixture metadata, sanitized aliases,
8-team snake scope, contiguous recovery ordering, and K/DEF reference behavior. It runs as part of
`./scripts/quality.sh docs` and makes no network requests.

## Evidence

- `sleeper-8-team-recovery-snapshot.json` is a synthetic, sanitized version of the documented
  draft and complete-current-picks response shape. It proves the offline handling requirements for
  an ordered partial draft snapshot, not a completed live draft.
- `sleeper-asset-reference-sample.json` supplies synthetic individual-player, kicker, and
  team-defense reference shapes. The `DEF` reference is an exact fixture-local provider mapping;
  it never relies on a display name.
- `observability-finding-2026-08-22.md` defines the activation rule, evidence hierarchy, recovery
  conditions, identity safe stops, API cadence, and implementation gate.
