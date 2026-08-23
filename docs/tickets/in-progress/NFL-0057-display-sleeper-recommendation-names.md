# NFL-0057 — Display Sleeper recommendation names

- Status: In Progress
- Resolution: Unresolved
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-24
- Updated: 2026-08-24
- Depends on: NFL-0045, NFL-0047

## Canonical sources

- [Architecture overview — Adapter boundary](../../architecture/overview.md#extension)
- [Protocol — Recommendations](../../contracts/protocol.md#recommendations)
- [Data and Player Identity — Sources and compliance](../../data/data-and-identity.md#sources-and-compliance)
- [Source inventory](../../data/source-inventory.md)

## Outcome

The Sleeper panel displays a current recommendation candidate's player name rather than its
internal ID, without persisting raw provider catalog labels in the backend or recommendation
dataset.

## In scope

- Add an exact provider reference to the additive recommendation response contract.
- Resolve only current candidate labels through the Sleeper service-worker adapter and render them
  in the content panel.
- Bound catalog retrieval, retain only an in-memory label map, and keep a usable recommendation
  state if a label cannot be resolved.

## Out of scope

- Changing rankings, persisting provider display names, altering immutable datasets, or supporting
  a new platform.

## Acceptance criteria

- [ ] The panel never renders an internal player ID as a candidate label.
- [ ] Provider display data remains service-worker-only and is not sent to the backend or stored.
- [ ] The additive HTTP contract, generated consumers, documentation, and tests agree.
- [ ] A catalog or network failure leaves recommendations current with an explicit label fallback.

## Validation

- [ ] Run the applicable backend, extension, documentation, and repository quality checks.
- [ ] Confirm no provider catalog payload or private draft data is committed.

## Blocker

None.

## Completion summary

Complete when the active Sleeper panel renders current candidate names using the verified extension
adapter path.

## History

- 2026-08-24 — Started after the live v4 panel exposed opaque internal recommendation IDs.
