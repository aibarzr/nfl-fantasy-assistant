# Domain Model

## Language and identity

- **Surface:** the website currently hosting the extension, such as FantasyPros.
- **League provider:** the system owning the fantasy league, initially ESPN.
- **Observation:** untrusted, repeatable information extracted by an adapter.
- **Accepted event:** an observation validated and applied exactly once.
- **Snapshot:** a point-in-time observation used to initialize or reconcile state.
- **Canonical state:** the last valid, persisted backend representation.
- **Player reference:** provider plus external ID, optionally accompanied by display fields.
- **Internal player:** the stable application entity to which external identities map.
- **Recommendation snapshot:** ranked output plus every input/version needed to reproduce it.

Names, abbreviations, team, and position are attributes, not identity. `gsis_id` is preferred when available, but a generated internal ID is always retained.

## Core entities

### LeagueConfig

Owns team count, draft type, ordered roster slots, bench slots, scoring rules, flex eligibility, superflex, and TE premium. It is immutable for an active draft version. League-format behavior must derive from this entity rather than scattered conditionals.

### DraftSession

Identified independently from the browser page and scoped to one league/draft. It records status, provider, user team/slot, draft order, current/next pick, pinned model/data versions, accepted picks, rosters, and reconciliation status.

Suggested lifecycle:

```text
DISCOVERED -> ACTIVE -> COMPLETE
     |          |
     v          v
  BLOCKED <-> RECONCILING
```

`BLOCKED` means recommendations cannot be trusted until a configuration, identity, or state conflict is resolved. It does not discard valid history. `COMPLETE` accepts no new picks unless an explicit correction workflow reopens the session.

### DraftPick

Contains overall pick number, round, pick-in-round, team ID, internal player ID, and source observation metadata. Overall pick number is unique within the session. A player may be drafted at most once, and each accepted pick must correspond to the configured draft order.

### TeamRoster

Is derived from accepted picks and `LeagueConfig`, not independently edited by browser observations. Slot assignment may be recalculated, but the selected players and legal-roster constraints must remain consistent.

### Player

Contains internal ID, available external IDs, display name, NFL team, position, and identity metadata. External-ID mappings are unique within `(provider, external_id)` unless explicitly quarantined as a data conflict.

### RecommendationSnapshot

Records pick context, timestamp, available-player set or stable reference to it, candidates and components, chosen action if known, league config version, model/feature/dataset versions, and source update times.

## Invariants

- Canonical state changes only through validated application operations committed to persistence.
- Accepted event IDs are unique per draft and repeat with the same payload/outcome.
- Reusing an accepted event ID with a materially different payload is a conflict.
- Accepted overall pick numbers are unique, monotonic in normal ingestion, and may contain a temporary observed gap only while reconciliation is required.
- Drafted players are absent from availability; unresolved observations do not silently remove a guessed player.
- Rosters are projections of accepted picks and the configured order.
- Replacement level and roster legality derive from the active league configuration.
- A draft pins versions; the same pinned inputs yield the same ranking.

## Identity resolution

Resolution proceeds by exact external mapping, then supported authoritative crosswalks, then controlled normalized-name candidates with corroborating team/position/rookie context. A name fallback is accepted only when it produces one sufficiently supported candidate under a versioned rule. Otherwise the observation remains unresolved.

Identity resolution returns a result such as `resolved`, `unresolved`, or `conflict` with provenance and method. It never mutates historical accepted identity silently when a source mapping changes.

## Reconciliation semantics

Compare a snapshot against accepted picks by overall pick number:

- Identical pick/team/player: no change.
- Snapshot contains an unobserved, resolvable next or gap pick: append in pick order and rebuild derived state atomically.
- Snapshot omits accepted trailing picks: treat it as incomplete unless the adapter proves snapshot completeness.
- Same pick number resolves to a different team or player: mark conflict and block fresh recommendations.
- Unresolved player: preserve the observation and request resolution; do not guess availability.

Reconciliation records its source, timestamp, differences, and outcome.

## Scoring and draft calculations

Fantasy points are calculated from explicit `LeagueConfig.scoring_rules`. Flex demand is derived from eligible positions and roster slots. League size affects replacement level, scarcity, future turn distance, and positional demand; no universal `QB12`/`RB30` constant is a domain rule.
