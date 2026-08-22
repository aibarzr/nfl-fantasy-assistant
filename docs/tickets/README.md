# Internal Ticketing

This directory is the task-level source of truth for planned, active, blocked, and completed work. Product behavior, architecture, domain semantics, protocol behavior, data policy, modeling rules, security controls, operations, and phase boundaries remain owned by their canonical documents. A ticket may link to and restate acceptance criteria from those documents, but it cannot redefine them.

## Layout and source of truth

```text
docs/tickets/
├── backlog/       approved or proposed work that has not started
├── in-progress/   work with an active owner
├── blocked/       started work that cannot advance
├── done/          completed work with validation evidence
└── TEMPLATE.md    required ticket structure
```

The containing directory is authoritative for status. The `Status` field inside a ticket must match it. Ticket IDs and filenames remain stable when files move between directories.

Files use `NFL-NNNN-short-kebab-title.md`. IDs are never reused or renumbered. The initial backlog uses sequential IDs; later tickets take the next unused number without filling gaps.

## Workflow

The normal flow is:

```text
backlog -> in-progress -> done
                |
                v
             blocked
                |
                v
           in-progress
```

- Move a backlog ticket to `in-progress/` only after its hard dependencies are done and an owner is assigned.
- Move active work to `blocked/` when it cannot advance. Record the cause, impact, and concrete unblock condition in the ticket.
- Move a ticket to `done/` only when every acceptance criterion is satisfied, applicable checks pass, and validation evidence is recorded.
- Reopen completed work by moving it to `in-progress/`, assigning an owner, and recording why its previous completion is no longer sufficient.
- If a ticket is cancelled or superseded, first update the canonical roadmap or specification that changed its necessity. Move it to `done/` with `Resolution: Cancelled` or `Resolution: Superseded` and record the replacement or rationale; it does not count as completed work in the phase summary.

Every transition updates the path, `Status`, `Updated`, and history in the same change. Update the phase summary when completion counts change. Do not use ticket notes as the sole record of a product, protocol, architectural, persistence, or security decision.

## Ticket readiness and completion

Before starting a ticket:

- Read its linked canonical sources and resolve any contradiction there first.
- Confirm that dependencies marked as hard are done.
- Ensure its outcome and acceptance criteria remain valid for the current phase.
- Set `Owner` to the person or agent doing the work.

Before completing a ticket:

- Check every acceptance criterion and applicable item in `docs/engineering/development.md`.
- Record exact checks and outcomes; do not invent commands before their toolchain exists.
- Update public documentation, contracts, generated consumers, or ADRs when required.
- Confirm no generated, local, restricted, or sensitive artifacts were added.
- Add a concise completion summary and set `Resolution: Done`.

## Phase summary

Folders and ticket contents remain authoritative; this table is only an aggregate view. Phase order and scope come from `docs/roadmap.md`.

| Phase | Planned | Done | Current state |
|---|---:|---:|---|
| 0 — Scaffolding | 4 | 4 | Complete |
| 1 — Technical spikes | 4 | 4 | Complete — findings and safe-stop limits recorded for the 8-team ESPN MVP |
| 2 — Data foundation | 6 | 6 | Complete — local immutable ingestion, curated/identity/feature transforms, baseline pool, and atomic versioned publication |
| 3 — Backend draft core | 9 | 9 | Complete — loopback FastAPI, SQLite canonical state, idempotent observations, reconciliation, derived rosters/availability, checked v1 contracts, and recommendation provenance |
| 4 — Baseline recommendation engine | 5 | 5 | Complete — deterministic projections, calibrated player value, dynamic replacement/VOR, explainable Top-N scoring, and time-safe promotion checks |
| 5 — Live platform loops | 10 | 4 | In progress — ESPN initialization is blocked on identity, semantic-codebook, and recovery evidence; Sleeper discovery is active over completed K/DEF neutral support |
| **Total** | **38** | **32** | |

FantasyPros as a browser surface, Monte Carlo simulation, and in-season modules remain deferred in the roadmap and have no executable tickets yet.

## Maintenance rules

- Keep one independently verifiable outcome per ticket, normally small enough for one reviewable change.
- Express ordering through phases and explicit dependencies; do not add time or point estimates.
- Prefer links to canonical sections over copied design prose.
- Preserve completed tickets as project history; do not rewrite their original acceptance criteria after closure.
- Never place credentials, real league data, unsanitized captures, machine paths, generated output, or restricted datasets in tickets or evidence.
