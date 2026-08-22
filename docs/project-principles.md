# NFL Fantasy Assistant — Project Principles

## Purpose

Build a browser-assisted NFL fantasy decision-support tool that observes a draft, maintains reliable local league state, ranks available players dynamically, and presents explainable recommendations in the browser.

The architectural north star is not merely “who is the best available player?” but:

> Which selection maximizes expected roster value given the league, roster, draft position, available players, uncertainty, and likely availability at future picks?

Reliability, explainability, modularity, and reproducibility take priority over sophistication.

## Stable principles

- Use a thin Chromium extension and a local Python decision engine.
- Keep platform-specific extraction behind adapters and all fantasy strategy in the backend.
- Treat browser input as observations; the persisted backend state is canonical.
- Prefer structured platform data, then browser-observable state, with DOM scraping as a controlled fallback.
- Reconstruct availability from the player pool and accepted picks; do not trust a virtualized visible list.
- Use stable internal domain models at subsystem boundaries.
- Never use player names as primary identity.
- Separate offline data preparation from the live decision path.
- Separate projected production, player value, and contextual draft decisions.
- Prefer deterministic baselines before ML and a reliable live loop before Monte Carlo simulation.
- Make events idempotent and repair missed observations through snapshots and reconciliation.
- Return Top-N recommendations with component scores and human-readable reasons.
- Version data, features, parameters, and models so recommendations can be reproduced.
- Keep platform permissions, localhost exposure, and stored secrets to the minimum needed.
- Follow KISS and YAGNI; prove one provider before generalizing to many.

## Non-goals for the MVP

- Waiver, start/sit, drop, or trade advice.
- Multiple simultaneous leagues.
- Mobile or remote/cloud operation.
- ML-based draft simulation.
- NCAA modeling or universal fantasy-platform support.

Future modules may reuse identity, projection, league configuration, and data-freshness infrastructure, but must not reuse draft strategy as if it were in-season strategy.

## Anti-patterns

Do not:

- Store authoritative draft state only in the extension or its service worker.
- Leak ESPN, FantasyPros, or nflverse records across their adapter/data boundaries.
- Equate real-world NFL performance with fantasy value.
- Use one undifferentiated player model for QB, RB, WR, and TE.
- Apply universal replacement levels or one static weight profile to every league and round.
- Double-count historical production after it already influences projections.
- Recompute historical datasets during a live draft.
- Hide identity uncertainty, failures, model components, or recommendation provenance.

## Canonical documentation

This document contains only durable principles. Exact product requirements, architectural behavior, contracts, domain rules, models, and operating procedures live in the documents linked from the repository `README.md` and `AGENTS.md`.
