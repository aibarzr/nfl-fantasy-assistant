# Recommendation Engine

## Layered model

Keep three independently testable questions separate:

1. **Projection:** how much fantasy production is expected from the player under the league scoring rules?
2. **Player value:** what is the player's context-independent draft value after calibrated market prior and uncertainty?
3. **Draft decision:** which available player best improves this roster at this pick, given replacement, future availability, constraints, and risk?

Historical features influence projection and must not be added again directly to the final draft score.

## Projection baseline

Start with deterministic position-specific weighted models over prepared semantic features. QB explicitly models rushing; RB receiving involvement responds to PPR; WR prioritizes target/air-yard opportunity; TE includes receiving role and later positional advantage. Availability, role stability, high-value usage, and efficiency remain distinct explainable inputs.

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

Explanations must reflect the actual calculation; they are not post-hoc generic text.

## Validation and promotion

Evaluate projection independently with MAE/RMSE, Spearman correlation, top-N and position-specific ranking quality. Evaluate decisions through deterministic historical draft simulations against ECR-only, ADP-only, best-player-available, static VOR, dynamic VOR, and incremental full-engine baselines.

Measure roster value, actual historical fantasy output without leakage, positional advantage, replacement value, and value captured. Segment results by position, league format, draft slot/stage, rookies, and confidence.

A model version is promoted only when:

- It is deterministic and reproducible from a published dataset.
- Component and end-to-end tests pass.
- Backtest inputs cannot include future information.
- It improves the declared primary metrics without unacceptable segment regressions.
- Parameters, normalization, data/features, results, and known limitations are recorded.

Never change the model or input dataset silently during an active draft.
