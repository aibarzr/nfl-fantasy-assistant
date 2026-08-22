# NFL-0002 — Scaffold extension toolchain and package structure

- Status: Done
- Resolution: Done
- Phase: 0 — Scaffolding
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: None

## Canonical sources

- [Development and Quality Guide](../../engineering/development.md#toolchain-status)
- [Architecture Overview](../../architecture/overview.md#extension)
- [Local Security Threat Model](../../security/threat-model.md#required-controls)

## Outcome

A minimal Manifest V3 extension skeleton with pinned tooling and explicit adapter, content, service-worker, API-client, and UI boundaries.

## Scope

Choose and configure the TypeScript package manager, compiler, formatting, linting, tests, and build tooling without introducing platform behavior or broad permissions.

## Acceptance criteria

- [x] The package layout keeps platform extraction behind adapters and fantasy strategy outside the extension.
- [x] The initial manifest is valid, contains no token, and grants only permissions required by the empty scaffold.
- [x] Exact install, format, lint, type-check, test, and build commands are documented in the development guide and `AGENTS.md`.
- [x] A minimal test/build proves the extension skeleton is reproducible.

## Validation

- [x] `npm --prefix extension ci`, formatting, lint, type-check, tests, and build pass on
  2026-07-29.
- [x] `.gitignore` excludes extension dependencies and output, credentials, and captures; the
  manifest grants only `storage` and no host permissions.

## Completion summary

Added a Manifest V3 TypeScript scaffold with committed npm lockfile, Biome, TypeScript, Vitest,
and a reproducible build. The package has explicit adapter, content, service-worker, API-client,
configuration, and UI boundaries without introducing any platform behavior or fantasy strategy.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-29 — Started by Codex.
- 2026-07-29 — Completed by Codex; validation evidence recorded above.
