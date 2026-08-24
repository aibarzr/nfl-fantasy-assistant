# Recommendation Engine

## Layered model

Keep three independently testable questions separate:

1. **Projection:** how much fantasy production is expected from the player under the league scoring rules?
2. **Player value:** what is the player's context-independent draft value after calibrated market prior and uncertainty?
3. **Draft decision:** which available player best improves this roster at this pick, given replacement, future availability, constraints, and risk?

Historical features influence projection and must not be added again directly to the final draft score.

## Projection baseline

Start with deterministic position-specific weighted models over prepared semantic features. QB
explicitly models rushing; RB receiving involvement responds to PPR; WR prioritizes target/air-yard
opportunity; TE includes receiving role and later positional advantage. K uses documented kicking
opportunity and conversion inputs; `DEF` uses documented team-defense scoring inputs. When a
league enables field-goal distance/miss bands or points-allowed bands, projection applies their
published per-game/rate features directly and rejects incomplete band coverage rather than
substituting a flat rule. K is projected as an individual player and `DEF` as a team asset. Neither
model may be enabled until its source coverage, scoring semantics, confidence behavior, and
validation segment are versioned.
Availability, role stability, high-value usage, and efficiency remain distinct explainable inputs.
Availability is unknown when an admitted source does not prove participation; the projector omits
that component, emits a warning, and applies a versioned confidence reduction rather than treating
unknown as healthy, inactive, or a neutral value.

Historical durability is an explainable participation proxy, not an injury diagnosis. It is built
from a complete eligible-week calendar and may provide four-game, eight-game, prior-season, and
recency-weighted multi-season rates. It stays null for incomplete evidence and is not promoted into
projection or draft-risk weights until its position-segmented, time-safe backtest passes.

Rookies follow a separate projector because missing NFL history is not negative evidence. The initial configurable prior is 50% ECR, 25% draft capital, 15% expected role/depth chart, and 10% athletic profile. NCAA production remains deferred.

Outputs include expected fantasy production, floor, ceiling, confidence, and component contributions. Every parameter set has a model version.

## Player value

The initial configurable baseline combines 65% normalized own-model value and 35% ECR-based prior. ECR dispersion, best/worst rank, freshness, and movement contribute to uncertainty when present. Backtesting, not preference, decides whether weights change.

Market consensus reduces early-model error but cannot be the sole ranking. Missing or stale market data yields an explicit confidence adjustment and configured fallback, never an unmarked zero.

## Draft decision baseline

For each available, eligible player:

```text
VOR = PlayerValue - dynamic ReplacementValue(position, league and draft state)

DraftScore = weighted normalized(
  VOR,
  next-pick urgency,
  positional scarcity,
  market value,
  roster fit,
  risk/upside
)
```

Dynamic replacement derives from teams, starting/flex slots, bench demand, drafted players, and current availability. Scarcity measures the projected positional drop from waiting and is distinct from current VOR. Urgency estimates whether a candidate is likely to survive to the user's next snake-draft pick.

Before simulation exists, urgency and expected next-pick value use deterministic ECR/ADP, uncertainty, picks-until-next-turn, and positional-demand approximations. Monte Carlo may replace those estimates only after it beats the baseline in isolated backtests.

## Initial weight profiles

All component inputs are normalized under a versioned method before weighting. Starting configurations are hypotheses:

| Stage | VOR | Urgency | Scarcity | Market | Roster | Risk/upside |
|---|---:|---:|---:|---:|---:|---:|
| Rounds 1–3 | 45% | 20% | 15% | 10% | 5% | 5% risk |
| Rounds 4–8 | 35% | 20% | 20% | 10% | 10% | 5% risk |
| Late | 25% | 15% | 15% | 5% | 20% | 20% upside |

Stage is derived from pick/roster state rather than treated as the only context. Large value advantages may outweigh soft roster needs. Hard legal constraints—such as too few remaining picks to fill required slots—may apply strong documented adjustments.

## Output and explanation

Return Top-N candidates, never only an opaque winner. Each includes:

- Rank, draft score, and confidence.
- Normalized component scores.
- Short reason codes and human-readable explanations tied to measured components.
- Relevant tier drop or next-pick survival estimate.
- Risk/freshness warnings.
- Model, feature, and dataset versions.
- Current-status overlay ID and observation time when current player-status evidence was available.

Current player status is provenance and explanation input, not a projection feature. Any change to
ranking, projection, or confidence policy requires separately versioned, calibrated evidence.

## Current-status and durability policy

`injury-risk-v1-warning-only` keeps the injury-neutral draft score and rank unchanged. It emits
`current_status_risk` and `historical_durability` components for explanation, then reduces only
confidence: 8% for unknown current status or unavailable durability, 4% for a non-healthy neutral
status, and 5% when complete historical durability is below 0.75. These multipliers are explicit
uncertainty behavior, not injury probabilities or value penalties. Current `healthy` removes the
status uncertainty reduction; unknown, stale, missing, contradictory, and unsupported evidence
remain unknown. No status automatically excludes a candidate, including reserve labels.

The policy consumes immutable historical durability from the prepared recommendation-input artifact
and a fresh (at most 36-hour) persisted neutral overlay. It retains the overlay ID/observation time
and `injury-risk-v1-warning-only` policy version in recommendation provenance. A stale overlay is
retained for replay but is not used as current evidence. Numeric projection or ranking penalties
remain disabled until a separately promoted calibrated parameter version beats the injury-neutral
baseline by the documented segment gates.

Explanations must reflect the actual calculation; they are not post-hoc generic text.

## Validation and promotion

Evaluate projection independently with MAE/RMSE, Spearman correlation, top-N and position-specific ranking quality. Evaluate decisions through deterministic historical draft simulations against ECR-only, ADP-only, best-player-available, static VOR, dynamic VOR, and incremental full-engine baselines.

Measure roster value, actual historical fantasy output without leakage, positional advantage,
replacement value, and value captured. Segment results by position (including K and DEF), league
format, draft slot/stage, rookies, confidence, current-status class, durability band, and roster
rules. A K/DEF model must not be promoted on aggregate
metrics alone when its position segment regresses or lacks coverage.

A model version is promoted only when:

- It is deterministic and reproducible from a published dataset.
- Component and end-to-end tests pass.
- Backtest inputs cannot include future information.
- It improves the declared primary metrics without unacceptable segment regressions.
- Parameters, normalization, data/features, results, and known limitations are recorded.

Never change the model or input dataset silently during an active draft.
