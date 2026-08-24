# NFL-0058 — Stop fabricating historical player availability

- Status: Done
- Resolution: Done
- Phase: 6 — Recommendation improvements
- Owner: Codex
- Created: 2026-08-24
- Updated: 2026-08-24
- Depends on: NFL-0012, NFL-0024, NFL-0042

## Canonical sources

- [Data and Player Identity](../../data/data-and-identity.md#feature-foundation)
- [Data and Player Identity](../../data/data-and-identity.md#quality-gates)
- [Offline Data Contract](../../data/offline-data-contract.md#identity-and-features)
- [Recommendation Engine](../../modeling/recommendation-engine.md#projection-baseline)

## Outcome

Historical availability is unknown unless supported by explicit source evidence, so projections no
longer receive a fabricated healthy signal from every player-stat row.

## Context

The current skill-position preparation path assigns `active=true` to every nflverse player-stat
observation. The four-observation availability transform therefore commonly reports full
availability even though the approved source inventory explicitly says not to assume injury or
participation coverage. This creates false precision in projection components and confidence.

## In scope

- Preserve missing availability evidence as null or an equivalent explicit unknown state from
  curation through prepared recommendation inputs.
- Remove the unconditional `active=true` assignment from source rows that do not prove game-day
  availability.
- Define deterministic missing-feature behavior that renormalizes supported projection evidence
  or applies a documented confidence penalty without substituting a healthy, inactive, or zero
  observation.
- Version affected schemas, features, projection parameters, prepared artifacts, warnings, and
  provenance; rebuild rather than mutate an existing immutable dataset version.
- Add fixture tests for known-active, unknown, missing, and stale evidence without future leakage.

## Out of scope

- Inferring that a missing stat line was caused by injury.
- Adding a new injury, participation, schedule, or provider source.
- Applying current injury-status penalties to draft ranking.

## Acceptance criteria

- [x] No source path marks a player active unless the consumed source field establishes that fact.
- [x] Unknown availability stays explicit through projection, confidence, warnings, publication,
  and recommendation provenance and is never silently converted to `1.0`, `0.0`, or a healthy
  observation.
- [x] Missing availability cannot improve a player's projected value relative to identical,
  supported healthy evidence merely because of a neutral-value substitution.
- [x] Existing immutable dataset versions and active drafts retain their pinned behavior; newly
  published versions carry new compatible feature/model/schema pins.
- [x] Canonical data, modeling, offline-contract, and operational documentation describe the
  corrected null and fallback semantics before or with implementation.

## Validation

- [x] Run applicable backend unit/integration tests, OpenAPI checks if shapes change, dataset
  reproducibility checks, `./scripts/quality.sh backend`, and `./scripts/quality.sh docs`.
- [x] Compare a fixture pool before and after the correction and record affected availability,
  confidence, warning, and ranking outputs.
- [x] Confirm no generated, local, restricted, or sensitive artifacts were committed.

## Completion summary

Removed fabricated `active=true` from historical skill-stat preparation; nullable availability now
flows through semantic features as `availability_unknown`, and projection-v4 omits it from the
weighted score while reducing confidence. Added source/feature/projection fixtures and preserved
legacy published recommendation inputs by reading their pinned model version. `./scripts/quality.sh
backend`, `./scripts/quality.sh docs`, and `git diff --check` passed.

## History

- 2026-08-24 — Created in Backlog after auditing the current injury and historical-availability
  behavior.
- 2026-08-24 — Started; auditing the feature, projection, dataset, and provenance paths.
- 2026-08-24 — Completed with feature-v4/projection-v4 unknown-availability semantics and
  reproducibility coverage.
