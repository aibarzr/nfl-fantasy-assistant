# NFL Fantasy Assistant

A local, browser-assisted decision-support tool for NFL fantasy drafts. A thin Chromium extension observes a supported draft surface; a local Python backend owns league state, resolves players, and returns explainable recommendations.

## Status

The project is in Phase 0: repository scaffolding. The backend and extension toolchains are
available, but there is no live draft runtime yet.

The first production target is an ESPN-backed 8-team snake draft, with recommendations refreshed in under one second. See the [MVP specification](docs/product/mvp-spec.md) for the exact boundary.

## Architecture

```text
ESPN/FantasyPros page
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
`AGENTS.md`. The current scaffold is intentionally inert: it has no platform host permissions,
HTTP API, persistence, or recommendation behavior.

Start with:

- [Project principles](docs/project-principles.md)
- [MVP specification](docs/product/mvp-spec.md)
- [Architecture overview](docs/architecture/overview.md)
- [Agent instructions](AGENTS.md)
- [Roadmap](docs/roadmap.md)
- [Internal ticketing and backlog](docs/tickets/README.md)

For live-draft recovery and diagnostics, use the [operations runbook](docs/operations/runbook.md).
