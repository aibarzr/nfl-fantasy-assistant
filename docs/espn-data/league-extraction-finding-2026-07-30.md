# ESPN league extraction finding — 2026-07-30

## Result

The sanitized structured response is sufficient to recognize the captured 8-team snake shape and
to preserve its scheduled draft order. It is deliberately insufficient to turn every numeric ESPN
configuration code into a semantic `LeagueConfig`, or to discover the current user's team without
a guess. Those gaps must be surfaced as explicit unsupported/configuration-unavailable outcomes.

| Neutral fact | Observed source | Result |
|---|---|---|
| Browser surface and league provider | Fixture metadata holds `surface: espn_draft` and `league_provider: espn` independently | Supported; never conflate the page hosting the extension with the provider that owns the league. |
| Team count | Structured `settings.size`, normalized as `snapshot.team_count` | Supported only when exactly `8`; the synthetic 10-team input produces `unsupported_team_count`. |
| Draft type and scheduled order | Structured draft settings and 128 one-based scheduled positions | Supported for observed `SNAKE`; all order entries use fixture-local opaque team references. |
| Roster and position limits | Structured numeric slot-count and position-limit maps | Source shape is observed, but numeric slot-code semantics are not established by this capture. Preserve codes inside the ESPN adapter only; reject an unknown/non-versioned codebook rather than labelling flex, superflex, or TE premium by inference. |
| Scoring | Structured scoring type plus 45 numeric stat-item values | Source shape is observed, but the stat-code-to-semantic-rule dictionary is not established. Do not claim PPR, TE premium, or any scoring rule merely from its numeric code. |
| User team and user slot | No sanitized structured field, browser state object, or DOM extraction rule in the evidence | Not supported by this capture. Return `user_slot_unavailable`; do not select a team from order, roster contents, display text, or a personal identifier. |

## Tests performed

`espn-8-team-initial-snapshot.json` supplies the representative configuration: exactly eight
teams, 128 scheduled picks, `SNAKE` draft type, a roster-code map, position limits, and 45 scoring
items. The fixture checker verifies the order and its sanitized team aliases.

`synthetic-unsupported-team-count-10.json` exercises the visible rejection outcome for a
configuration outside the 8-team-only MVP. It is intentionally not represented as an ESPN
capture.

## Implementation boundary and protocol clarification

The extension adapter may normalize only observed provider facts: provider, surface, team count,
draft type, opaque team references, scheduled order, raw roster-code map, and raw scoring-item
map. The backend derives no missing user slot, flex semantics, or scoring semantics from those
facts.

Before an adapter is implemented, the neutral initial-snapshot protocol must require a user team
reference and user slot together, or a stable unavailable/unsupported outcome. A supported request
must additionally carry a versioned ESPN slot/stat codebook result; raw ESPN numeric codes are not
domain `LeagueConfig` semantics.

To unblock full ESPN league initialization, capture and sanitize one browser-visible source that
relates the active user to exactly one team, and an authorized semantic codebook/source for every
nonzero roster and scoring code in the supported configuration. Do not solve either gap with a
name, a URL identifier, or a hard-coded assumption.
