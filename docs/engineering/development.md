# Development and Quality Guide

## Toolchain status

The Phase 5 project uses uv 0.12.0 with Python 3.14.4 for the backend, and npm with Node 22.18.0
for the extension. Backend dependencies are locked in `backend/uv.lock`; extension dependencies
are locked in `extension/package-lock.json`. FastAPI/OpenAPI is the implemented local protocol
boundary.

Run these commands from the repository root. They are intentionally identical to the command
table in `AGENTS.md`.

| Component | Install | Format | Format check | Lint | Type-check | Test | Build | Run |
|---|---|---|---|---|---|---|---|---|
| Backend | `uv --directory backend sync --all-groups --frozen` | `uv --directory backend run ruff format .` | `uv --directory backend run ruff format --check .` | `uv --directory backend run ruff check .` | `uv --directory backend run mypy src tests` | `uv --directory backend run pytest` | `uv --directory backend build` | `uv --directory backend run python -m nfl_fantasy_assistant --help` |
| Extension | `npm --prefix extension ci` | `npm --prefix extension run format` | `npm --prefix extension run format:check` | `npm --prefix extension run lint` | `npm --prefix extension run typecheck` | `npm --prefix extension test` | `npm --prefix extension run build` | Load `extension/dist` as an unpacked extension only to validate a provider adapter; no provider has yet passed the full live-loop acceptance fixture. |

Contract generation/checking does not exist until the FastAPI/OpenAPI boundary is introduced;
do not substitute handwritten wire types for it. The repository-wide command and CI workflow are
introduced by NFL-0003.

## Repository quality workflow

After installing both toolchains, run `./scripts/quality.sh all`. It runs backend checks,
extension checks, local documentation-link validation, then checks that no tracked file drift was
created. Component-specific invocations are `./scripts/quality.sh backend`,
`./scripts/quality.sh extension`, `./scripts/quality.sh docs`, and `./scripts/quality.sh drift`.
Each failure prints the component and exact command. CI runs the same workflow and independently
fails on a Git diff. No OpenAPI contract command is present until a generated contract exists.

## Local pairing configuration

Copy `backend/config.example.toml` into the private configuration directory selected for the
machine, then initialize a token with
`uv --directory backend run python -m nfl_fantasy_assistant pair init --config-dir <config-dir>`.
The command writes a mode-600 `backend.token` and prints the token once. In the extension
service-worker developer-tools console—not a website console or page DOM—run:

```js
await chrome.storage.local.set({
  pairedBackendConfiguration: {
    baseUrl: "http://127.0.0.1:8765",
    bearerToken: "<token-printed-by-the-backend>",
  },
});
```

Rotate with `uv --directory backend run python -m nfl_fantasy_assistant pair rotate --config-dir <config-dir>`;
then explicitly re-pair the extension. Revoke with
`uv --directory backend run python -m nfl_fantasy_assistant pair revoke --config-dir <config-dir>`.
Once `config.toml` and `backend.token` are installed in the default private configuration
directory, `uv --directory backend run python -m nfl_fantasy_assistant --check-config` validates
the loopback-only non-secret settings and paired token without displaying the token.
Do not store a real token in shell history, source, fixtures, URLs, a page DOM, or logs.

### Sleeper initialization context

Sleeper initialization additionally needs the operator's stable opaque Sleeper user ID and the
exact published dataset, feature, and model versions. Set them only in the extension service-worker
developer-tools console after the local runtime reports all three as ready:

```js
await chrome.storage.local.set({
  sleeperInitializationConfiguration: {
    userId: "<stable-sleeper-user-id>",
    datasetVersion: "<published-dataset-version>",
    featureVersion: "<published-feature-version>",
    modelVersion: "<published-model-version>",
  },
});
```

The adapter verifies that ID against the documented league user, roster, slot, and (when present)
draft-order facts. It never derives the account from a name, URL, creator metadata, page DOM, or
browser authentication. Do not use a website console, retain a provider response, or commit this
per-device configuration.

To activate Sleeper identity resolution, start the backend with the explicit immutable published
crosswalk dataset directory (not its mutable publication root or a loose Parquet file):

```sh
uv --directory backend run python -m nfl_fantasy_assistant serve \
  --config-dir <config-dir> \
  --prepared-dataset <published-sleeper-dataset-version-directory>
```

The server validates the manifest/checksums and activates only exact prepared-pool mappings. It
does not import raw source data. A derived runtime version with
`prepared_recommendation_inputs.parquet` additionally activates deterministic recommendation
generation; a legacy identity-only version remains safe for initialization but reports
recommendations unavailable. Build a new current pool and then derive/publish a new Sleeper
crosswalk version to add that artifact—never edit an existing version. An incompatible version pin
is rejected before draft creation.

## Repository boundaries

```text
extension/    adapter, content, service worker, API client, browser UI
backend/      API adapters, application/domain, data, models, persistence
data/         local raw/curated/cache artifacts when introduced; ignored by VCS
docs/         canonical design and operating documentation
tests/        cross-component fixtures/tests if not colocated by toolchain
```

Use explicit types at boundaries and pure functions for scoring/state rules where practical. Configuration owns model parameters and environment-specific behavior; avoid magic constants in business code.

## Configuration and sensitive material

- Non-secret defaults may live in versioned configuration.
- Tokens, platform credentials, user league data, real captured payloads, databases, and machine paths remain untracked.
- Provide sanitized examples for every required local setting.
- Validate configuration at startup and report missing/unsupported values without printing secrets.

## Tests

### Extension

Test hostname/surface detection, adapter parsing, documented provider-API and DOM fallbacks,
snapshot extraction/completeness, event-ID creation/deduplication, protocol serialization, status
UI, and service-worker/page recovery. Use saved sanitized HTML/response fixtures; normal CI must
not depend on live ESPN, Sleeper, or FantasyPros pages.

### Backend

Test domain invariants, scoring rules, identity outcomes (including individual K and team-defense
assets), draft transitions, idempotency, snapshot reconciliation/conflicts, replacement level,
VOR, scarcity, urgency, roster constraints, persistence/restart, error mapping, and reproducibility.

### Data and models

Test schema/lineage checks, transformations on small fixtures, time-safe feature generation,
scoring at each position (including K/DEF), normalization, explanation fidelity, model-version
pinning, and deterministic backtests.

### Integration and performance

Maintain a deterministic 8-team PPR snake fixture with a known player pool, draft order, duplicate event, missed pick, unknown identity, restart, and expected recommendations. Measure observation-to-response and response-to-render; the full local update budget is under one second.

## Quality gates

Every change runs applicable formatting checks, lint, static typing, unit tests, contract checks, and builds. Contract changes also regenerate/check TypeScript types and exercise compatibility/error cases. Data/model changes run leakage, reproducibility, and relevant backtest checks. Documentation links and examples must remain valid.

CI must not modify tracked files. Generated output is checked by regenerating it and failing on drift.

## Definition of Done

A change is complete when:

- Behavior matches the MVP/domain/architecture documents.
- Tests cover the success path and material failure/idempotency cases.
- Errors are visible and existing valid state is preserved.
- Structured logs add useful correlation without sensitive data.
- Public contracts and generated consumers agree.
- Required documentation and ADRs are updated.
- Performance/reproducibility budgets remain satisfied where affected.

## Fixtures and live investigation

Technical spikes may inspect live browser/network behavior manually. Before committing a fixture, remove tokens, cookies, account/league/team identifiers, personal names, and unrelated payload fields. Record surface, capture date, expected parser outcome, and whether the fixture is complete or partial.

## Database and generated artifacts

Once persistence exists, schema changes use forward migrations tested from every supported prior application version; do not edit an existing applied migration. Database schema/migrations are authoritative for physical storage, while the domain document remains authoritative for semantics.

Generated OpenAPI clients/types, coverage, builds, caches, databases, and prepared datasets are not edited manually or treated as source documentation.
