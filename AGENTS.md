# NFL Fantasy Assistant Agent Instructions

## Read first

Use the narrowest relevant source of truth before changing the project:

- Product behavior and acceptance: `docs/product/mvp-spec.md`
- System boundaries and dependency direction: `docs/architecture/overview.md`
- Domain terms, state, and invariants: `docs/domain/domain-model.md`
- Extension/backend wire semantics: `docs/contracts/protocol.md`
- Data sources and player identity: `docs/data/data-and-identity.md`
- Projection and recommendation logic: `docs/modeling/recommendation-engine.md`
- Development workflow and quality gates: `docs/engineering/development.md`
- Security decisions: `docs/security/threat-model.md`
- Live-draft operations: `docs/operations/runbook.md`
- Current delivery phase: `docs/roadmap.md`
- Task backlog and delivery status: `docs/tickets/README.md`

If documents disagree, stop and resolve the contradiction in the canonical document. Do not encode a new interpretation only in code.

## Architectural constraints

1. Keep platform-specific behavior behind extension adapters.
2. Keep fantasy strategy and canonical draft state out of the extension.
3. Keep backend domain logic independent from FastAPI and persistence implementations.
4. Keep nflverse-specific records inside the backend data layer.
5. Use internal domain models at module boundaries.
6. Keep projection, player valuation, and draft decision logic separate.
7. Prefer deterministic, explainable implementations before ML or simulation.
8. Make scoring components independently testable and model parameters versioned.
9. Treat draft events as idempotent observations; persist and reconcile canonical state in the backend.
10. Never use a player name as a primary identity or guess a critical identifier.
11. Do not add support or abstraction for an unimplemented provider without a demonstrated need.
12. Every recommendation must be reproducible from stored state, data version, and model version.

## Working rules

- Use the Markdown ticket workflow in `docs/tickets/README.md` for task-level planning and status. Tickets never override canonical product or technical documentation.
- Preserve the `extension/`, `backend/`, and offline-data boundaries described in the architecture.
- Update the canonical protocol before or with a wire-contract change. Once the backend exists, Pydantic/OpenAPI is authoritative for exact HTTP shapes; TypeScript types must be generated from or checked against it.
- Add a short ADR under `docs/architecture/decisions/` for decisions that alter system boundaries, protocol ownership, persistence technology, or another costly-to-reverse choice.
- Do not hand-edit generated API clients, schemas, datasets, migrations, build output, or caches.
- Keep secrets and real platform payloads out of fixtures and logs. Sanitize captured HTML/network responses.
- Add or update tests for changed behavior and documentation for changed public behavior.

## Commands and completion

Use the following commands from the repository root. `uv` 0.12.0 is the Python project
manager; Python 3.14.4 is selected in `backend/.python-version`. Node 22.18.0 is required for
the extension.

| Component | Install | Format | Format check | Lint | Type-check | Test | Build | Run |
|---|---|---|---|---|---|---|---|---|
| Backend | `uv --directory backend sync --all-groups --frozen` | `uv --directory backend run ruff format .` | `uv --directory backend run ruff format --check .` | `uv --directory backend run ruff check .` | `uv --directory backend run mypy src tests` | `uv --directory backend run pytest` | `uv --directory backend build` | `uv --directory backend run python -m nfl_fantasy_assistant --help` |
| Extension | `npm --prefix extension ci` | `npm --prefix extension run format` | `npm --prefix extension run format:check` | `npm --prefix extension run lint` | `npm --prefix extension run typecheck` | `npm --prefix extension test` | `npm --prefix extension run build` | Load `extension/dist` as an unpacked extension after the build; it has no active platform behavior in Phase 0. |

Contract generation/checking does not exist until the FastAPI/OpenAPI boundary is introduced; do
not substitute handwritten wire types for it. After both installs, run
`./scripts/quality.sh all`; its component forms are `./scripts/quality.sh backend`,
`./scripts/quality.sh extension`, `./scripts/quality.sh docs`, and `./scripts/quality.sh drift`.
CI runs the same workflow and fails if it produces tracked-file drift.

For local pairing, use
`uv --directory backend run python -m nfl_fantasy_assistant pair init --config-dir <config-dir>`.
Rotate with `uv --directory backend run python -m nfl_fantasy_assistant pair rotate --config-dir <config-dir>`
and revoke with
`uv --directory backend run python -m nfl_fantasy_assistant pair revoke --config-dir <config-dir>`.
The extension configuration must be written only from an extension context into
`chrome.storage.local`, as specified in the development guide and ADR-0001.
`uv --directory backend run python -m nfl_fantasy_assistant --check-config` validates the default
local non-secret settings and pairing without printing the token.

A change is complete only when the applicable checks in `docs/engineering/development.md` pass, contracts and documentation remain aligned, and no generated or sensitive data is accidentally included.
