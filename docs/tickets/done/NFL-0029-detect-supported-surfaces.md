# NFL-0029 — Implement exact surface detection and minimal extension permissions

- Status: Done
- Resolution: Done
- Phase: 5 — ESPN live loop
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0002, NFL-0005

## Canonical sources

- [MVP Specification](../../product/mvp-spec.md#functional-requirements)
- [Local Security Threat Model](../../security/threat-model.md#required-controls)

## Outcome

The extension activates only on exact supported ESPN host/surface rules and requests the minimum browser and loopback permissions required for the live loop.

## Scope

Implement hostname/subdomain and page-context detection, distinguish surface from league provider, validate content/service-worker messages, and expose unsupported/incompatible status without state mutation.

## Acceptance criteria

- [x] Supported and lookalike/unsupported hostnames are distinguished exactly.
- [x] Page messages are checked for origin, shape, size, operation, and supported surface.
- [x] Manifest permissions are documented, minimal, and contain no deferred FantasyPros surface support.
- [x] Incompatible page shape stops observations and emits actionable diagnostics.

## Validation

- [x] `espn-surface.test.ts` covers the confirmed surface, deceptive suffixes, subdomains, HTTP, unsupported paths, wrong origins/sources, malformed/unsupported operations, oversized messages, and incompatible pages.
- [x] Built-manifest review confirms exactly `storage`, the loopback and confirmed ESPN host permissions, one exact-path content-script match, and no FantasyPros or embedded pairing material.

## Reopened evidence

On 2026-07-31 an operator supplied a mock-draft URL. The canonical observability finding now
retains only its exact non-identifying surface rule: `https://fantasy.espn.com/football/draft`.
Its query parameters and identifiers were discarded. This unblocks exact host/page-context
detection and minimal permissions; it does not establish league initialization or recovery data.

## Completion summary

Implemented the exact confirmed ESPN draft-surface guard, strict page-message validation, and the
minimal documented Chromium permissions. The supplied URL was sanitized to host and pathname only;
no league, team, or member identifier was retained.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex; canonical sources were reviewed.
- 2026-07-31 — Blocked by missing canonical exact-host/page-context evidence; no host permission or detection rule was guessed.
- 2026-07-31 — Reopened by Codex after sanitized operator-confirmed host/path evidence was recorded in the observability finding.
- 2026-07-31 — Completed by Codex.
