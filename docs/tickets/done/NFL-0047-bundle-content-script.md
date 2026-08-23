# NFL-0047 — Bundle the extension content script

- Status: Done
- Resolution: Done
- Phase: 5 — Live platform loops
- Owner: Codex
- Created: 2026-08-23
- Updated: 2026-08-23
- Depends on: NFL-0046

## Canonical sources

- [Architecture overview — Extension](../../architecture/overview.md#extension)
- [Development guide — Toolchain status](../../engineering/development.md#toolchain-status)

## Outcome

The unpacked Manifest V3 extension loads its content lifecycle on supported draft pages without
classic-script module syntax errors.

## Context

Chrome executes manifest-declared content scripts as classic JavaScript. The TypeScript compiler
preserves the content entrypoint's ES module imports, preventing the lifecycle from starting on
Sleeper. The build must emit a bundled classic script while preserving the module service worker.

## In scope

- Bundle the content-script entrypoint into a classic browser script.
- Fail the build if static module syntax remains in that output.
- Record the dependency and validation evidence.

## Out of scope

- Changing Sleeper API access, page behavior, or draft/recommendation logic.
- Altering the module service-worker build.

## Acceptance criteria

- [x] `content/index.js` contains no static `import` or `export` syntax and loads as the manifest content script.
- [x] The extension build, static checks, and tests pass.
- [x] No generated extension output, private configuration, or provider data is committed.

## Validation

- [x] `npm --prefix extension run build` emitted an IIFE content script and rejected residual static module syntax.
- [x] `npm --prefix extension run test` passed 56 tests; format, lint, and type checks passed.
- [x] `./scripts/quality.sh all` passed all component checks; its tracked-drift step correctly reported the uncommitted source change.

## Completion summary

Chrome's supported Sleeper page progressed past the previous `Cannot use import statement outside a
module` error and rendered the draft-companion panel. The build now bundles the content entrypoint
with esbuild as a classic IIFE while leaving the Manifest V3 service worker as a module.

## History

- 2026-08-23 — Created in progress after Chrome reported `Cannot use import statement outside a module` for `content/index.js` on the supported Sleeper page.
- 2026-08-23 — Completed after the rebuilt unpacked extension rendered its content panel; extension checks passed.
