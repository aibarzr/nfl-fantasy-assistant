# NFL-0004 — Design and implement local configuration and secure token pairing

- Status: Done
- Resolution: Done
- Phase: 0 — Scaffolding
- Owner: Codex
- Created: 2026-07-29
- Updated: 2026-07-29
- Depends on: NFL-0001, NFL-0002

## Canonical sources

- [Local Security Threat Model](../../security/threat-model.md#token-lifecycle)
- [Operations Runbook](../../operations/runbook.md#installation-and-startup-checklist)

## Outcome

The backend and extension share a locally generated token through a documented pairing, rotation, and revocation flow without exposing it to page context or source control.

## Scope

Record the chosen mechanism in an ADR, implement validated non-secret configuration and secret storage on both sides, and provide sanitized local examples. Runtime API enforcement is completed in NFL-0017.

## Acceptance criteria

- [x] The ADR covers generation, storage, pairing, rotation, revocation, diagnosis, and rejected alternatives.
- [x] Token generation uses a cryptographically secure local source and the token never enters URLs, DOM, bundles, fixtures, or logs.
- [x] Missing and mismatched configuration fails visibly without revealing secrets.
- [x] Backup/export behavior excludes the token by default.

## Validation

- [x] Backend and extension tests cover initial pairing, mismatch validation, rotation, revocation, re-pairing, and loopback-only non-secret configuration validation on 2026-07-29.
- [x] Reviewed source and configuration examples: they contain only a placeholder token and no machine-specific path. No real token was generated during validation, and the pairing implementation writes no logs.

## Completion summary

Implemented CSPRNG token generation, atomic private backend storage, validated loopback-only
non-secret settings, token rotation/revocation, secret-free diagnostics, and default backup
exclusion. The extension validates loopback pairing values and persists them only in
`chrome.storage.local`; ADR-0001 and the runbook define the operator flow without putting a token
in a page context.

## History

- 2026-07-29 — Created in Backlog.
- 2026-07-29 — Started by Codex after NFL-0001 and NFL-0002 completed.
- 2026-07-29 — Completed by Codex; validation evidence recorded above.
- 2026-07-29 — Reopened during the completion audit to add executable non-secret backend configuration validation.
- 2026-07-29 — Re-completed by Codex after the added configuration test passed.
