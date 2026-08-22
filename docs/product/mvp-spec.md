# MVP Specification

## Goal

During one supported ESPN or Sleeper fantasy draft, detect draft changes, update a reliable local
representation, recompute recommendations in less than one second, and display an explainable
Top-N list in the active Chromium page.

## Supported matrix

| Capability | MVP support |
|---|---|
| Browser | Chromium-based desktop browsers |
| League provider | ESPN or Sleeper |
| Browser surface | Exact confirmed ESPN or Sleeper desktop draft surface; FantasyPros remains deferred |
| Active leagues | One at a time |
| League sizes | 8 teams |
| Draft | Snake, known user slot |
| Scoring and roster | Configurable QB/RB/WR/TE/K/DEF, bench, and documented-flex values representable by `LeagueConfig`; unsupported rules are rejected visibly |
| Runtime | Local extension and backend only |
| Recommendations | Top-N, deterministic, component-scored, human-readable |

Auctions, keepers, dynasty-specific rules, best ball, mobile browsers, cloud backends, FantasyPros,
and providers other than ESPN or Sleeper are outside the MVP unless explicitly added here.

## Primary user journey

1. The user starts the local backend and loads the configured extension.
2. The extension recognizes a supported surface and checks backend health and authentication.
3. The adapter obtains league settings, draft order, user team, current picks, and player
   references from a validated structured provider source where available; browser state and DOM
   parsing remain fallbacks that require their own evidence.
4. The backend creates or resumes the draft, resolves identities, and reconciles the initial snapshot.
5. Each observed pick is submitted idempotently and updates canonical state.
6. The backend ranks currently available players using the pinned data and model versions.
7. The extension renders Top-N recommendations, confidence, component scores, and concise reasons.
8. Periodic snapshots repair missed events. Reloads and service-worker suspension resume the same draft.

## Functional requirements

- **FR-01 Surface detection:** identify each supported provider surface by exact hostname and path
  rules, and distinguish browser surface from league provider.
- **FR-02 League initialization:** capture team count, draft type, roster slots, scoring, draft order, user team, and user slot or reject the configuration visibly. Kicker (`K`) and team defense (`DEF`) are supported roster categories; flex eligibility is explicit rather than inferred.
- **FR-03 Draft observation:** use a documented structured provider source where appropriate,
  with browser state and DOM parsing as fallbacks only after their shape and completeness are
  validated.
- **FR-04 Event ingestion:** attach a stable `event_id`; repeated submission must have no second effect.
- **FR-05 Reconciliation:** accept authoritative-enough pick snapshots, compare them with canonical state, and repair only unambiguous divergence.
- **FR-06 Identity:** resolve platform IDs to internal draftable assets; a kicker is an individual player and `DEF` is a team-defense asset. Never silently resolve solely by an ambiguous name.
- **FR-07 Availability:** derive available players from the prepared pool minus accepted picks.
- **FR-08 Recommendation:** return ranked candidates based on league-aware value and current draft state.
- **FR-09 Explainability:** include normalized components, confidence, model/data versions, and reasons for every returned candidate.
- **FR-10 Persistence:** persist league, draft, picks, rosters, mappings, and recommendation snapshots.
- **FR-11 Recovery:** browser reload, extension-worker restart, or backend restart must not corrupt a valid draft.
- **FR-12 Diagnostics:** expose health and diagnostics sufficient to distinguish connection, data, identity, adapter, and model failures.

## Degraded and failure behavior

- With the backend unavailable or unauthorized, show a visible connection status and retry safely; do not pretend recommendations are current.
- For an unknown player, retain the observation, flag it for resolution, and preserve existing valid availability rather than guessing.
- For duplicate events, return the previously established outcome.
- For gaps or conflicts, request/submit a snapshot and surface an unresolved state when it cannot be repaired safely.
- For stale datasets, show freshness and continue only when the configured policy permits it.
- For unsupported league rules, do not silently approximate the league.
- When the adapter detects an incompatible page shape, stop mutating state from that source and provide diagnostics.

## Non-functional requirements

- The event-to-render path must complete in under one second under the deterministic fixture workload, excluding platform network delay.
- The API binds to `127.0.0.1` by default and requires the configured shared token.
- The same canonical state, league config, dataset version, feature version, and model version produce the same recommendation.
- The live path uses prepared features/projections and performs no historical ingestion.
- Logs are structured, correlated by league/draft/event where applicable, and never contain tokens.

## Acceptance criteria

Each supported provider is accepted separately when an end-to-end deterministic 8-team fixture proves that:

1. The surface, league settings, draft order, and user slot are correct.
2. Picks are reliably detected, identified, persisted, and removed from availability.
3. Duplicate events and a missed-event snapshot reconcile without duplicate picks or lost valid state.
4. The backend remains canonical across page, service-worker, and backend restarts.
5. A versioned deterministic model returns a league-aware Top-N list with reasons.
6. The update is rendered within the latency budget.
7. Replaying the stored inputs under the same versions reproduces the recommendation.

Sleeper may use its documented read-only API only through its extension adapter, under the approved
source inventory and the security controls for remote provider access. FantasyPros remains deferred.
