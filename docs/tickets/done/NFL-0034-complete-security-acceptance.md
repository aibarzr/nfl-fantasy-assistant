# NFL-0034 — Complete loopback, messaging, redaction, and permission security acceptance

- Status: Done
- Resolution: Done
- Phase: 5 — ESPN live loop
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-31
- Depends on: NFL-0017, NFL-0029, NFL-0032

## Canonical sources

- [Local Security Threat Model](../../security/threat-model.md#security-acceptance)
- [Development Guide](../../engineering/development.md#configuration-and-sensitive-material)

## Outcome

Automated and documented security acceptance demonstrates that untrusted pages, local callers, malformed inputs, logs, fixtures, and extension permissions cannot bypass required controls or corrupt state.

## Scope

Cover unauthorized loopback access, CORS/origin, token lifecycle, message-source validation, payload bounds, database/path safety, dependency/permission review, and sanitization/redaction.

## Acceptance criteria

- [x] Unauthorized/disallowed/malformed/oversized calls receive stable failures and cause no partial mutation.
- [x] Pairing, rotation, revocation, and page/service-worker trust boundaries pass adversarial tests.
- [x] Logs, diagnostics, fixtures, exports, and packages contain no token, cookie, credential, or unsanitized account data.
- [x] Manifest and dependency permissions are minimal, pinned, reviewed, and reproducible.

## Validation

- [x] Backend API tests cover authenticated/disallowed-origin access, CORS preflight, malformed and oversized requests with no partial state, safe diagnostics, pairing lifecycle, loopback binding, and safe database paths. Extension tests cover exact-origin/window/shape/size/operation message gates, worker token isolation, rotation, and manifest permissions.
- [x] `./scripts/quality.sh all`, `./scripts/check-openapi-contract.sh`, the fixture sanitizer, and a built-artifact scan for account-query, cookie, and bearer-token patterns completed without sensitive values. Backup/export has no secret paths; no export bundle exists before the deferred operations ticket.

## Completion summary

Completed automated loopback, CORS, mutation-boundary, pairing, page/worker messaging, fixture,
permission, package, and redaction acceptance. The security checks preserve canonical state on
failure and confirm the exact ESPN/loopback manifest scope.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-31 — Started by Codex after NFL-0029 and NFL-0032 completed.
- 2026-07-31 — Completed by Codex.
