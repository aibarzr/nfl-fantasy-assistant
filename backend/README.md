# Backend draft core

This package provides the offline data foundation, loopback draft core, and deterministic baseline
recommendation engine. It exposes a FastAPI v1 boundary, SQLite-backed canonical draft state,
idempotent observations, reconciliation, reproducible recommendation-snapshot persistence, and
versioned projection, valuation, replacement, and draft-ranking components. Platform observation
remains an extension-adapter responsibility.

`src/nfl_fantasy_assistant/domain` is framework- and persistence-independent. Outer adapters
belong in `api`, `data`, and `persistence`; application orchestration belongs in `application`.

The data package ingests approved nflverse inputs through `nflreadpy` into local immutable source
snapshots, converts fixture-sized or local inputs into typed Parquet tables, resolves external IDs,
derives leakage-safe weekly semantic features, prepares a deterministic baseline pool, and
atomically publishes validated dataset versions. Local source/cache/published files belong under
the ignored `data/` directory; source data and credentials must never be committed.

Run the service only after private pairing/configuration: `uv run python -m
nfl_fantasy_assistant serve --config-dir <config-dir>`. The server remains bound to `127.0.0.1`.
