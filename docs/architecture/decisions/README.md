# Architecture Decision Records

Use an ADR for a decision that changes a costly-to-reverse architectural boundary, contract owner, persistence approach, trust boundary, or major dependency. Routine implementation details belong in code and its tests.

## Naming

Use `NNNN-short-kebab-title.md`, starting at `0001`. Never renumber accepted records. Superseded records remain in place and link to their replacement.

## Statuses

`Proposed`, `Accepted`, `Superseded`, or `Rejected`.

## Template

```markdown
# NNNN — Decision title

- Status: Proposed
- Date: YYYY-MM-DD
- Supersedes: none

## Context

What forces and constraints require a decision?

## Decision

What is the chosen behavior or boundary?

## Consequences

What becomes easier, harder, required, or deliberately unsupported?

## Alternatives considered

Which credible alternatives were rejected, and why?
```

The existing baseline decisions are captured in the project principles and architecture overview. Create individual ADRs when implementation validates or changes a decision whose rationale must be preserved; do not manufacture retrospective records for every guideline.
# Architecture Decisions

- [ADR-0001: Local token pairing](0001-local-token-pairing.md)
- [ADR-0002: Extension-bound provider API access](0002-extension-bound-provider-api-access.md)
- [ADR-0003: Model team defenses as draftable assets](0003-model-team-defenses-as-draftable-assets.md)
- [ADR-0004: Identity-only observed Sleeper assets](0004-identity-only-observed-sleeper-assets.md)
- [ADR-0005: Wikidata external-identity candidates](0005-wikidata-external-identity-candidates.md)
- [ADR-0006: Versioned current player-status overlay](0006-versioned-current-status-overlay.md)
