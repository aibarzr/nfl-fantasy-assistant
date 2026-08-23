# NFL-0040 — Implement Sleeper extension adapter

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0037, NFL-0038

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#primary-user-journey)
- [Architecture Overview](../../architecture/overview.md#platform-adapter-strategy)
- [Extension–Backend Protocol](../../contracts/protocol.md#approved-provider-expansion)
- [Sleeper observability finding](../../sleeper-data/observability-finding-2026-08-22.md)
- [Threat Model](../../security/threat-model.md#required-controls)

## Outcome

The extension recognizes only the confirmed Sleeper NFL draft surface and, through its service
worker, translates validated documented API snapshots into neutral initialization, event, and
reconciliation requests.

## In scope

- Extend the authoritative v1 API contract and generated TypeScript types for `sleeper` provider,
  `sleeper` surface, and `sleeper_api` complete snapshots.
- Add exact surface activation, narrow manifest permissions, service-worker-only documented API
  retrieval, response validation, and bounded recovery handling.
- Translate documented complete ordered picks into stable neutral references and idempotent event
  IDs; reject malformed, cross-scoped, non-snake, non-8-team, incomplete, or unresolved inputs.
- Add sanitized synthetic fixtures and extension/backend contract tests.

## Out of scope

- Draft selection automation, DOM-as-source fallback, API credentials, raw payload retention, and
  support for a second provider framework.
- Enabling an initialized live draft before NFL-0039 has validated every required prepared-pool
  asset against the pinned Sleeper crosswalk.

## Acceptance criteria

- [x] The exact Sleeper surface and only that surface activates the adapter.
- [x] Provider requests originate only in the service worker after activation and validate bounded
  response shape, draft identity, 8-team snake order, and complete contiguous picks.
- [x] Initialization/recovery serializes only generated neutral contract types, including K/DEF
  references; malformed/unresolved data creates no backend mutation.
- [x] Events are deterministic and idempotent by scoped draft ID plus pick number; reload and
  worker restart reconcile from the complete snapshot.
- [x] The adapter refuses live initialization when the pinned prepared-pool crosswalk gate is not
  satisfied.

## Blocker

None. NFL-0039 still prevents live initialization by design; the completed adapter leaves that
gate closed rather than creating a backend league/draft or submitting draft-state mutations.

## Implementation progress

The authoritative v1 contract now admits Sleeper event and `sleeper_api` snapshot values and its
generated TypeScript consumer is synchronized. The extension manifest has only the Sleeper page
and documented API host permissions; its content lifecycle activates only on the confirmed
`/draft/nfl/<opaque-id>` surface. A pure recovery translator accepts only a draft-scoped,
contiguous, bounded 8-team pick snapshot and produces neutral `sleeper_api` references plus
deterministic event IDs. On the exact active surface, the content script asks the service worker to
read only the documented draft and picks endpoints; the worker rechecks the surface, requires
paired local configuration, bounds response size, and makes no backend mutation. DOM fallback and
live initialization remain absent.

## Completion summary

Completed with exact-surface activation, service-worker-only documented draft/picks reads, bounded
response handling, strict eight-team snake and slot-to-roster validation, and generated neutral
K/DEF snapshot types. Unsafe recovery inputs never construct a backend client or produce a backend
mutation; the absent prepared-pool crosswalk remains an explicit live-initialization stop.

## History

- 2026-08-23 — Started after the user requested the Sleeper extension implementation; recorded the
  prepared-pool identity gate as a hard activation stop.
- 2026-08-23 — Extended the checked v1 contract and added exact surface recognition, connected UI
  state, and synthetic complete-snapshot translation tests. The extension and backend checks pass;
  service-worker API retrieval and gated initialization remain.
- 2026-08-23 — Added service-worker-only documented draft/picks retrieval with exact-surface,
  response-size, draft-scope, 8-team snake, and contiguous-snapshot checks. It is read-only and
  reports a validated recovery snapshot without submitting a draft mutation.
- 2026-08-23 — Completed strict recovery validation: raw pick metadata, snake slot order, and
  draft slot-to-roster consistency must all validate before a neutral snapshot exists. Synthetic
  lifecycle and service-worker tests prove exact-surface activation, no backend client/mutation for
  unsafe data, fresh recovery after worker reload, K/DEF references, deterministic event IDs, and
  the prepared-pool gate. The source inventory and operations/protocol documentation now authorize
  only this bounded, on-demand recovery read; live initialization remains unavailable.
