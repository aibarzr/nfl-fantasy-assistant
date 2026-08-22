# NFL Fantasy Assistant

A local, browser-assisted decision-support tool for NFL fantasy drafts. A thin Chromium extension observes a supported draft surface; a local Python backend owns league state, resolves players, and returns explainable recommendations.

## Status

The project is in Phase 5: live platform loops. The backend draft core and deterministic
recommendation engine are implemented; the ESPN loop is partially implemented but blocked on
validated initialization and recovery evidence. Sleeper has been approved as a separate,
extension-bound adapter; its read-only discovery spike is active. Kicker and team-defense support
are implemented in the neutral backend/data/model; Sleeper still requires its own validated
adapter and identity/recovery evidence before a league can initialize.

The supported target scope is an 8-team NFL snake redraft on ESPN or Sleeper, with
recommendations refreshed in under one second under the deterministic fixture workload. See the
[MVP specification](docs/product/mvp-spec.md) for the exact boundary.

## Architecture

```text
ESPN/Sleeper page
        |
Chromium extension (observe, normalize, render)
        |
HTTP + bearer token on 127.0.0.1
        |
Python backend (canonical state, identity, valuation, decisions)
        |
SQLite + prepared Parquet data
```

The extension never owns canonical draft state or recommendation strategy. Historical processing runs offline rather than in the live draft path. See the [architecture overview](docs/architecture/overview.md).

## Repository

```text
extension/   Chromium extension
backend/     Python backend and offline data tooling
docs/        Product, architecture, protocol, and operating documentation
```

Local datasets, caches, build output, credentials, and real platform captures must not be
committed.

## Development

Install and quality commands are in [the development guide](docs/engineering/development.md) and
`AGENTS.md`. The local runtime requires installed dependencies, private pairing configuration,
and a published prepared dataset; it is not ready for a live draft until the relevant provider
adapter has passed its acceptance evidence.

Start with:

- [Project principles](docs/project-principles.md)
- [MVP specification](docs/product/mvp-spec.md)
- [Architecture overview](docs/architecture/overview.md)
- [Agent instructions](AGENTS.md)
- [Roadmap](docs/roadmap.md)
- [Internal ticketing and backlog](docs/tickets/README.md)

For live-draft recovery and diagnostics, use the [operations runbook](docs/operations/runbook.md).
