# Extension scaffold

The extension supports only the confirmed ESPN desktop draft surface
`https://fantasy.espn.com/football/draft`; query identifiers are never retained in source,
fixtures, logs, or diagnostics. It requests exactly `https://fantasy.espn.com/*` for that content
surface and `http://127.0.0.1/*` for the paired local backend, plus `storage` for pairing. It has
no FantasyPros permission or adapter.

Its source boundaries are intentional: platform extraction remains under `src/adapters`, page
lifecycle under `src/content`, localhost serialization under `src/api`, service-worker-only
configuration under `src/config`, and rendering under `src/ui`. Recommendation strategy and
canonical state belong to the backend.
