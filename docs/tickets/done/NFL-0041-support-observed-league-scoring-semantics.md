# NFL-0041 — Support observed league scoring semantics

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0024, NFL-0038

## Canonical sources

- [Domain Model](../../domain/domain-model.md#scoring-and-draft-calculations)
- [Data and Player Identity](../../data/data-and-identity.md#feature-foundation)
- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)
- [Sleeper observability finding](../../sleeper-data/observability-finding-2026-08-22.md)

## Outcome

The neutral data, scoring, and projection boundaries can reproduce the approved eight-team
league's explicit K and DEF scoring semantics without requiring an operator to simplify the
league's Sleeper settings.

## Context

An operator-authorized inspection of the private test league on 2026-08-23 confirmed an eight-team
snake redraft with K and DEF. Its scoring includes field-goal distance bands, field-goal miss
bands, points-allowed bands, sacks, interceptions, fumble recoveries, safeties, and defensive
return touchdowns. Current neutral scoring accepts only flat field-goal values and linear
points/yards allowed; the K/DEF PBP transform does not retain all event/range inputs required to
reproduce this configuration. The operator chose to preserve the league rather than alter it.

The exact league ID, invite link, member data, and raw page/API payload remain local and are not
ticket evidence or fixtures.

## In scope

- Define neutral, versioned scoring semantics for the observed field-goal distance and miss bands
  and team-defense points-allowed bands.
- Retain the required approved PBP inputs through curated K/DEF features without fabricating
  statistics or converting them to player identities.
- Extend deterministic scoring/projection calculations so those semantics are reproducible from a
  published dataset and explicit `LeagueConfig.scoring_rules`.
- Add sanitized synthetic fixtures for boundary values, missed kicks, defensive events, and
  points-allowed ranges; verify deterministic scoring and position-specific behavior.
- Document the neutral codebook and data/projection contract before or with code changes.

## Out of scope

- Changing the Sleeper league, its scoring settings, or its commissioner configuration.
- Retaining the operator's real league payload, identifiers, or draft observations.
- Sleeper host permissions, polling, draft-event observation, or the extension adapter's runtime
  implementation.
- Market rankings, historical projection recalibration, or a current-season dataset build.

## Acceptance criteria

- [x] Every enabled observed K/DEF rule has an explicit neutral semantic representation or is
  rejected before a draft/session can be initialized; no rule is silently approximated.
- [x] K/DEF curated inputs and deterministic scoring reproduce synthetic field-goal and
  points-allowed boundary fixtures with explicit provenance and no future leakage.
- [x] Projection behavior remains independently testable and versioned for every supported
  position; existing flat scoring remains compatible.
- [x] The exact observed Sleeper configuration maps through the extension boundary without a
  platform-specific rule entering the backend domain.
- [x] Canonical data, domain, modeling, protocol, and operational documentation remain aligned.

## Validation

- [x] Run applicable backend formatting, lint, type, test, build, documentation, and OpenAPI
  contract checks.
- [x] Verify fixtures are synthetic and contain no live Sleeper payloads, identifiers, or secrets.

## Blocker

None.

## Completion summary

Completed with a sanitized configuration fixture proving the enabled K/DEF scoring semantics,
strict extension-boundary translation to neutral `LeagueConfigInput`, PBP-boundary coverage, and
versioned deterministic projection behavior. `./scripts/quality.sh all` passed after the coherent
Sleeper foundation commit, including generated-contract and clean-worktree drift checks.

The reopened current-league verification is now also complete: the translator maps the observed
`fum_lost`, `sack`, `int`, `fum_rec`, `fum_rec_td`, and `safe` keys to the neutral codebook. PBP
now treats documented blocked field goals and PATs as kicker misses. No raw league response or
identifier was retained.

## History

- 2026-08-23 — Created after the operator chose to preserve scoring revealed through an authorized
  local extension inspection, rather than simplify the league to the initial flat K/DEF codebook.
- 2026-08-23 — Added neutral semantic-v3 field-goal distance/miss bands and defensive
  points-allowed bands, with mutual-exclusion validation against flat rules. The K/DEF PBP
  transform now retains those bands and safeties from synthetic regular-season rows. Added a
  strict Sleeper adapter-side translator that rejects unknown, invalid, duplicate, or conflicting
  enabled provider scoring keys. Backend and extension checks pass.
- 2026-08-23 — Completed the semantic path: curated K rows now retain missed extra points; feature
  version 3 carries K band rates and DEF points-allowed/event rates without future leakage; and
  projection-v3 applies enabled bands to those explicit rates or fails closed for missing coverage.
  Added a pure Sleeper league-configuration boundary that maps the approved synthetic eight-team
  snake roster/scoring shape to neutral `LeagueConfigInput` and rejects unknown provider tokens.
  `quality.sh backend`, `quality.sh extension`, and `quality.sh docs` passed; the OpenAPI contract
  check passed. `quality.sh drift` correctly reports the existing uncommitted active-ticket work.
- 2026-08-23 — A read-only operator-authorized extension inspection reconfirmed that the visible
  eight-team snake and K/DEF scoring labels/values match the sanitized fixture. No provider IDs,
  invite data, raw responses, or browser-authentication material were retained. Added a
  fail-closed extra-point outcome check; backend, extension, documentation, OpenAPI, and build
  checks passed again.
- 2026-08-23 — Tightened missingness semantics: only a complete PBP transform may emit zero for an
  unused K scoring band. Source-unavailable values remain null and force a banded projection to
  reject incomplete coverage. Synthetic PBP tests now exercise every field-goal and points-allowed
  boundary plus an unrepresentable extra-point outcome.
- 2026-08-23 — Completed after `a5042a7` and a clean `./scripts/quality.sh all`: backend format,
  lint, type-check, 94 tests, OpenAPI contract, and build; extension format, lint, type-check, 32
  tests, and build; documentation/sanitization; and tracked/staged drift checks all passed.
- 2026-08-23 — Reopened after an authorized current-league read proved that the real enabled
  Sleeper D/ST keys are `sack`, `int`, `fum_rec`, `fum_rec_td`, and `safe`, rather than the
  unobserved `def_*` aliases accepted by the original translator. The previous completion is not
  sufficient until the adapter maps the observed keys to the neutral semantic codebook and its
  tests cover that exact configuration.
- 2026-08-23 — Completed the reopened work: extension tests cover the observed key vocabulary;
  backend tests cover blocked FG/PAT miss semantics; and the real local prepared-pool build accepts
  the resulting neutral configuration.
