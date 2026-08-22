# Extension–Backend Protocol

## Scope and ownership

The extension communicates with the local backend through versioned JSON over HTTP at `http://127.0.0.1:<configured-port>/v1`. Platform objects are translated to neutral types before transmission.

Before implementation, this document owns protocol semantics. After FastAPI models exist, backend Pydantic models and their generated OpenAPI own exact field shapes and validation constraints. TypeScript request/response types must be generated from or checked against that OpenAPI; copied handwritten wire models are not a second authority.

## Implemented v1 authority

Phase 3 implements the v1 boundary. [The generated OpenAPI document](../../backend/openapi.json)
is produced from `backend/src/nfl_fantasy_assistant/api/app.py`; its generated TypeScript consumer
types are `extension/src/api/generated-contract.ts`. Regenerate both with
`uv --directory backend run python scripts/generate_openapi.py --openapi openapi.json --typescript ../extension/src/api/generated-contract.ts`.
`./scripts/check-openapi-contract.sh` regenerates into a temporary directory and fails on drift.
The generated artifacts, rather than this explanatory prose, are authoritative for exact fields.

`health` is the only unauthenticated resource. All other resources require a matching bearer token
and the configured exact extension origin. Draft-state mutations expose their resulting `revision`.
An unavailable or non-current recommendation returns a stable `503` error rather than labeling an
older result as current.

## Common rules

- JSON field names use `snake_case` on the wire.
- IDs are opaque non-empty strings; clients must not parse meaning from them.
- Timestamps are UTC RFC 3339 strings, for example `2026-09-02T14:21:00Z`.
- Overall picks are one-based positive integers.
- Unknown enum values are rejected as unsupported rather than silently coerced.
- Every response has a request correlation ID header; errors also include it in the body.
- Mutating requests use `Content-Type: application/json` and bearer authentication.

## Authentication

All endpoints except health require `Authorization: Bearer <token>`. The token is configured through the local installation/pairing flow, not embedded in source code or page-accessible DOM. Missing or invalid credentials return `401` without revealing state. Origin and CORS policy follow the threat model.

## Resources

The MVP protocol provides these operations; exact schemas are introduced with the backend OpenAPI:

- `GET /v1/health` — process liveness and compatible API version, with no sensitive diagnostics.
- `GET /v1/diagnostics` — authenticated readiness, data/model versions, freshness, and actionable component status.
- `POST /v1/leagues` — validate/upsert neutral league metadata and configuration.
- `POST /v1/drafts` — initialize or resume a draft from league identity and initial snapshot.
- `POST /v1/drafts/{draft_id}/events` — submit one idempotent observation.
- `POST /v1/drafts/{draft_id}/snapshot` — reconcile a declared-completeness snapshot.
- `GET /v1/drafts/{draft_id}` — canonical state summary and unresolved issues.
- `GET /v1/drafts/{draft_id}/recommendations` — latest valid recommendations and provenance.

Creation operations return stable internal resource IDs. A platform league ID is namespaced by provider and is not itself the internal ID.

## Neutral references and observations

Illustrative semantics, not a substitute for OpenAPI:

```json
{
  "provider": "espn",
  "external_id": "4427366",
  "name": "Optional display hint",
  "position": "RB",
  "nfl_team": "ABC"
}
```

```json
{
  "event_id": "espn:league-123:draft-2026:pick-27",
  "observed_at": "2026-09-02T14:21:00Z",
  "surface": "fantasypros",
  "league_provider": "espn",
  "type": "player_drafted",
  "pick": 27,
  "team_id": "team-4",
  "player": {
    "provider": "espn",
    "external_id": "4427366"
  }
}
```

An event includes only the facts observed. Backend-derived round, roster assignment, availability, or scores must not be supplied as authoritative browser facts.

A snapshot includes its scope/completeness declaration, league configuration version or content,
draft order when available, user team reference and user slot when supported, and ordered picks.
The user team reference and user slot are supplied together; an adapter that cannot observe both
returns a stable unavailable/unsupported outcome rather than guessing. Raw provider roster or
scoring codes must be translated through a versioned adapter codebook before they are presented as
semantic league configuration. Partial snapshots may diagnose or append evidence but cannot prove
that accepted state should be deleted.

## Idempotency, ordering, and conflicts

- `event_id` is the idempotency key within a draft.
- Replaying the same semantic event returns the established outcome and does not recalculate a second state transition.
- Reusing the ID with different material data returns `409 event_id_conflict`.
- A future pick with missing predecessors returns an accepted-needs-reconciliation or conflict outcome defined by the OpenAPI operation; it is never silently reordered.
- State-changing responses expose the resulting canonical revision. Requests may include the last observed revision where optimistic conflict detection is useful.

## Recommendations

Each candidate contains internal player ID, rank, draft score, confidence, normalized component scores, concise reason codes/text, and relevant uncertainty/freshness warnings. The response contains draft revision, generated timestamp, model version, feature version, dataset version, and source-update metadata.

If state is blocked or inputs violate freshness policy, the endpoint returns an explicit non-current status and issues; it must not label an old result as current.

## Error envelope

Non-success responses use stable machine-readable codes:

```json
{
  "error": {
    "code": "unknown_player",
    "message": "The player reference could not be resolved safely.",
    "request_id": "req-opaque",
    "retryable": false,
    "details": {}
  }
}
```

Use `400` for malformed semantics, `401` for authentication, `404` for absent resources, `409` for state/idempotency conflicts, `422` for schema validation, `429` only for explicit protection, and `503` for temporary unavailable/not-ready dependencies. Domain-specific error codes remain stable within `/v1`.

## Compatibility

Additive optional response fields are compatible. Removing/renaming fields, changing their meaning, tightening previously accepted input, or changing state semantics requires a new API version or a coordinated compatibility window. Persisted events retain the protocol version with which they were accepted.
