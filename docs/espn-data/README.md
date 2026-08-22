# Sanitized ESPN Spike Evidence

This directory contains only sanitized, reviewable fixture material and documentation for the
Phase 1 ESPN technical spikes. It must never contain raw HAR files, cookies, authorization
headers, bearer/access/refresh tokens, full URLs with account/league/member parameters, or real
league/member/team identifiers.

Raw captures are local-only material under `data/raw/espn/`, which is ignored by version control.
They must be rotated/sanitized before any derivative is copied here. A fixture must state its
surface, capture date, completeness, source class, and expected parser outcome.

Regenerate the derived fixtures with `node scripts/sanitize_espn_spike_captures.mjs`. The script
accepts only the expected local raw capture names, emits a deliberately narrow subset, replaces
real team identifiers with fixture-local aliases, and refuses to write known credential/identifier
classes into this directory. `node scripts/check_espn_spike_fixtures.mjs` validates the committed
fixtures' metadata, 8-team scope, normalized event/player references, and absence of known secret
or name fields; it runs as part of `./scripts/quality.sh docs`.

## Fixtures

- [`synthetic-unsupported-team-count-10.json`](synthetic-unsupported-team-count-10.json) is a
  synthetic rejection input derived from the observed `settings.size` field shape. It validates
  the unsupported-team-count path for the 8-team-only MVP; it is not evidence of a real ESPN
  10-team capture.
- `espn-8-team-initial-snapshot.json` is the sanitized initial configuration and scheduled-order
  fixture.
- `espn-8-team-selected-picks.json` is the normalized sequence of observed pick messages.
- Its `source_trailing_numeric_code` is intentionally not interpreted as an overall pick: repeated
  values are evidence that NFL-0005 must establish the source event/idempotency semantics before
  adapter implementation.
- `espn-player-reference-sample.json` records non-name ESPN player references by position code.
- [`observability-finding-2026-07-30.md`](observability-finding-2026-07-30.md) ranks the observed
  configuration and event channels, records their limits, and defines the explicit recovery safe
  stop. It is the Phase 1 conclusion for the captured 8-team surface and records the sanitized
  activation rule `https://fantasy.espn.com/football/draft` (no query identifiers retained).
- [`league-extraction-finding-2026-07-30.md`](league-extraction-finding-2026-07-30.md) records
  which 8-team configuration facts are safe to normalize and the explicit unsupported outcomes
  for the unobserved user slot and unverified numeric code semantics.
- [`player-identity-finding-2026-07-30.md`](player-identity-finding-2026-07-30.md) documents the
  observed ESPN reference namespace and the versioned nflverse ESPN-to-GSIS crosswalk route.
