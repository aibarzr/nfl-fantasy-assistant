"""Deterministic, position-specific fantasy projection models.

The projection layer consumes only stable semantic features and league scoring.  It has no draft
session, roster, persistence, or browser dependency, so its outputs can be evaluated separately
from valuation and draft decisions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from nfl_fantasy_assistant.domain.scoring import (
    DEFENSIVE_POINTS_ALLOWED_BANDS,
    FIELD_GOAL_MADE_BANDS,
    FIELD_GOAL_MISSED_BANDS,
    validate_scoring_rules,
)

SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE", "K", "DEF"})


class ProjectionError(ValueError):
    """A semantic projection input or parameter set is invalid."""


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _normalized(value: float | None, scale: float) -> float | None:
    return None if value is None else _clamp(value / scale)


@dataclass(frozen=True, slots=True)
class ProjectionFeatures:
    """Stable semantic feature inputs, all measured before the projection decision point."""

    usage_per_game: float | None = None
    opportunity_per_game: float | None = None
    efficiency_per_opportunity: float | None = None
    high_value_usage_per_game: float | None = None
    receiving_role: float | None = None
    rushing_role: float | None = None
    role_stability: float | None = None
    availability_rate: float | None = None
    durability_rate: float | None = None
    historical_points_per_game: float | None = None
    kicking_attempts_per_game: float | None = None
    kicking_conversion_rate: float | None = None
    extra_point_attempts_per_game: float | None = None
    extra_points_made_per_game: float | None = None
    extra_points_missed_per_game: float | None = None
    field_goals_made_0_19_per_game: float | None = None
    field_goals_made_20_29_per_game: float | None = None
    field_goals_made_30_39_per_game: float | None = None
    field_goals_made_40_49_per_game: float | None = None
    field_goals_made_50_plus_per_game: float | None = None
    field_goals_missed_0_19_per_game: float | None = None
    field_goals_missed_20_29_per_game: float | None = None
    field_goals_missed_30_39_per_game: float | None = None
    field_goals_missed_40_49_per_game: float | None = None
    field_goals_missed_50_plus_per_game: float | None = None
    defensive_sacks_per_game: float | None = None
    defensive_interceptions_per_game: float | None = None
    defensive_fumble_recoveries_per_game: float | None = None
    defensive_safeties_per_game: float | None = None
    turnovers_forced_per_game: float | None = None
    points_allowed_per_game: float | None = None
    defensive_touchdowns_per_game: float | None = None
    defensive_points_allowed_0_rate: float | None = None
    defensive_points_allowed_1_6_rate: float | None = None
    defensive_points_allowed_7_13_rate: float | None = None
    defensive_points_allowed_14_20_rate: float | None = None
    defensive_points_allowed_21_27_rate: float | None = None
    defensive_points_allowed_28_34_rate: float | None = None
    defensive_points_allowed_35_plus_rate: float | None = None
    source_updated_at: datetime | None = None

    def normalized(self) -> dict[str, float | None]:
        """Use explicit, versioned semantic scales rather than source-column magnitudes."""
        return {
            "usage": _normalized(self.usage_per_game, 25.0),
            "opportunity": _normalized(self.opportunity_per_game, 30.0),
            "efficiency": _normalized(self.efficiency_per_opportunity, 2.0),
            "high_value_usage": _normalized(self.high_value_usage_per_game, 5.0),
            "receiving_role": _clamp(self.receiving_role)
            if self.receiving_role is not None
            else None,
            "rushing_role": _clamp(self.rushing_role) if self.rushing_role is not None else None,
            "role_stability": _clamp(self.role_stability)
            if self.role_stability is not None
            else None,
            "availability": _clamp(self.availability_rate)
            if self.availability_rate is not None
            else None,
            "durability": _clamp(self.durability_rate)
            if self.durability_rate is not None
            else None,
            "historical_points": _normalized(self.historical_points_per_game, 30.0),
            "kicking_attempts": _normalized(self.kicking_attempts_per_game, 5.0),
            "kicking_conversion": _clamp(self.kicking_conversion_rate)
            if self.kicking_conversion_rate is not None
            else None,
            "extra_point_opportunity": _normalized(self.extra_point_attempts_per_game, 5.0),
            "defensive_sacks": _normalized(self.defensive_sacks_per_game, 5.0),
            "turnovers_forced": _normalized(self.turnovers_forced_per_game, 4.0),
            "points_allowed": (
                _clamp(1.0 - self.points_allowed_per_game / 35.0)
                if self.points_allowed_per_game is not None
                else None
            ),
            "defensive_touchdowns": _normalized(self.defensive_touchdowns_per_game, 0.5),
        }


@dataclass(frozen=True, slots=True)
class RookiePrior:
    """Non-NFL-history inputs for the explicitly separate rookie projector."""

    ecr_rank: int | None = None
    draft_capital_score: float | None = None
    expected_role_score: float | None = None
    athletic_score: float | None = None

    def values(self) -> dict[str, float | None]:
        return {
            "ecr": _clamp(1.0 - ((self.ecr_rank - 1) / 299)) if self.ecr_rank else None,
            "draft_capital": _clamp(self.draft_capital_score)
            if self.draft_capital_score is not None
            else None,
            "expected_role": _clamp(self.expected_role_score)
            if self.expected_role_score is not None
            else None,
            "athletic": _clamp(self.athletic_score) if self.athletic_score is not None else None,
        }


@dataclass(frozen=True, slots=True)
class ProjectionInput:
    internal_player_id: str
    position: str
    features: ProjectionFeatures
    is_rookie: bool = False
    rookie_prior: RookiePrior | None = None

    def __post_init__(self) -> None:
        if not self.internal_player_id or self.position not in SUPPORTED_POSITIONS:
            raise ProjectionError("projection requires an internal ID and supported position")
        if self.is_rookie and self.rookie_prior is None:
            raise ProjectionError("rookie projections require an explicit rookie prior")
        if not self.is_rookie and self.rookie_prior is not None:
            raise ProjectionError("veteran projections cannot include rookie-only prior inputs")
        if self.position == "DEF" and self.is_rookie:
            raise ProjectionError("team-defense assets cannot use rookie priors")


@dataclass(frozen=True, slots=True)
class ProjectionParameters:
    """All deterministic feature/scoring weights, with a reproducibility version."""

    model_version: str = "projection-v4"
    normalization_version: str = "semantic-v4"
    stale_after_days: int = 14
    position_weights: Mapping[str, Mapping[str, float]] = field(
        default_factory=lambda: {
            "QB": {
                "usage": 0.18,
                "opportunity": 0.16,
                "efficiency": 0.14,
                "high_value_usage": 0.12,
                "rushing_role": 0.24,
                "role_stability": 0.08,
                "availability": 0.04,
                "historical_points": 0.04,
            },
            "RB": {
                "usage": 0.20,
                "opportunity": 0.18,
                "efficiency": 0.10,
                "high_value_usage": 0.16,
                "receiving_role": 0.14,
                "rushing_role": 0.08,
                "role_stability": 0.08,
                "availability": 0.03,
                "historical_points": 0.03,
            },
            "WR": {
                "usage": 0.24,
                "opportunity": 0.20,
                "efficiency": 0.12,
                "high_value_usage": 0.08,
                "receiving_role": 0.18,
                "role_stability": 0.08,
                "availability": 0.04,
                "historical_points": 0.06,
            },
            "TE": {
                "usage": 0.20,
                "opportunity": 0.18,
                "efficiency": 0.12,
                "high_value_usage": 0.10,
                "receiving_role": 0.20,
                "role_stability": 0.08,
                "availability": 0.05,
                "historical_points": 0.07,
            },
            "K": {
                "kicking_attempts": 0.35,
                "kicking_conversion": 0.20,
                "extra_point_opportunity": 0.15,
                "role_stability": 0.10,
                "availability": 0.10,
                "historical_points": 0.10,
            },
            "DEF": {
                "defensive_sacks": 0.20,
                "turnovers_forced": 0.20,
                "points_allowed": 0.20,
                "defensive_touchdowns": 0.10,
                "role_stability": 0.10,
                "availability": 0.10,
                "historical_points": 0.10,
            },
        }
    )
    rookie_weights: Mapping[str, float] = field(
        default_factory=lambda: {
            "ecr": 0.50,
            "draft_capital": 0.25,
            "expected_role": 0.15,
            "athletic": 0.10,
        }
    )

    def __post_init__(self) -> None:
        if not self.model_version or not self.normalization_version or self.stale_after_days < 1:
            raise ProjectionError("projection parameters require versions and positive freshness")
        if set(self.position_weights) != SUPPORTED_POSITIONS:
            raise ProjectionError("position parameters must cover every supported position exactly")
        for weights in (*self.position_weights.values(), self.rookie_weights):
            if not weights or any(weight < 0 for weight in weights.values()):
                raise ProjectionError("projection weights must be non-negative and non-empty")
            if abs(sum(weights.values()) - 1.0) > 0.000001:
                raise ProjectionError("each projection weight profile must sum to one")


@dataclass(frozen=True, slots=True)
class PlayerProjection:
    internal_player_id: str
    position: str
    expected_points: float
    floor_points: float
    ceiling_points: float
    confidence: float
    components: Mapping[str, float]
    warnings: tuple[str, ...]
    model_version: str
    normalization_version: str


def _banded_scoring_component(
    scoring_rules: Mapping[str, float],
    features: ProjectionFeatures,
    rules: frozenset[str],
    feature_suffix: str,
) -> float:
    """Score exact band semantics only when every required historical rate is available."""
    enabled = sorted(rule for rule in rules if rule in scoring_rules)
    if not enabled:
        return 0.0
    rates = {rule: getattr(features, f"{rule}_{feature_suffix}") for rule in rules}
    missing = sorted(rule for rule in enabled if rates[rule] is None)
    if missing:
        raise ProjectionError(
            "banded scoring requires complete curated feature coverage: " + ", ".join(missing)
        )
    return sum(float(scoring_rules[rule]) * float(rates[rule]) for rule in enabled)


def _feature_scoring_component(
    scoring_rules: Mapping[str, float],
    features: ProjectionFeatures,
    rule_features: Mapping[str, str],
) -> float:
    """Apply an enabled rule to its explicit historical rate, never an implicit proxy."""
    component = 0.0
    for rule, feature_name in rule_features.items():
        if rule not in scoring_rules:
            continue
        value = getattr(features, feature_name)
        if value is None:
            raise ProjectionError(
                f"{rule} scoring requires curated feature coverage: {feature_name}"
            )
        component += float(scoring_rules[rule]) * value
    return component


def _scoring_adjustment(
    position: str, scoring_rules: Mapping[str, float], features: ProjectionFeatures
) -> float:
    """Represent the documented scoring sensitivity using explicit representative stat lines."""
    reception = float(scoring_rules.get("receptions", 0.0))
    rushing = float(scoring_rules.get("rushing_yards", 0.0)) * 10
    passing = (
        float(scoring_rules.get("passing_yards", 0.0)) * 250
        + float(scoring_rules.get("passing_touchdowns", 0.0)) * 2
    )
    if position == "QB":
        return (passing + rushing) / 24.0
    if position == "RB":
        return (reception * 4 + rushing) / 16.0
    if position == "K":
        made = _banded_scoring_component(scoring_rules, features, FIELD_GOAL_MADE_BANDS, "per_game")
        missed = _banded_scoring_component(
            scoring_rules, features, FIELD_GOAL_MISSED_BANDS, "per_game"
        )
        flat_made = 0.0
        if "field_goals_made" in scoring_rules:
            if (
                features.kicking_attempts_per_game is None
                or features.kicking_conversion_rate is None
            ):
                raise ProjectionError(
                    "field_goals_made scoring requires kicking attempt and conversion coverage"
                )
            flat_made = (
                float(scoring_rules["field_goals_made"])
                * features.kicking_attempts_per_game
                * features.kicking_conversion_rate
            )
        flat_missed = 0.0
        if "field_goals_missed" in scoring_rules:
            if (
                features.kicking_attempts_per_game is None
                or features.kicking_conversion_rate is None
            ):
                raise ProjectionError(
                    "field_goals_missed scoring requires kicking attempt and conversion coverage"
                )
            flat_missed = (
                float(scoring_rules["field_goals_missed"])
                * features.kicking_attempts_per_game
                * (1.0 - features.kicking_conversion_rate)
            )
        return (
            made
            + missed
            + flat_made
            + flat_missed
            + _feature_scoring_component(
                scoring_rules,
                features,
                {
                    "extra_points_made": "extra_points_made_per_game",
                    "extra_points_missed": "extra_points_missed_per_game",
                },
            )
        ) / 4.0
    if position == "DEF":
        points_allowed = _banded_scoring_component(
            scoring_rules, features, DEFENSIVE_POINTS_ALLOWED_BANDS, "rate"
        )
        return (
            _feature_scoring_component(
                scoring_rules,
                features,
                {
                    "defensive_sacks": "defensive_sacks_per_game",
                    "defensive_interceptions": "defensive_interceptions_per_game",
                    "defensive_fumble_recoveries": "defensive_fumble_recoveries_per_game",
                    "defensive_touchdowns": "defensive_touchdowns_per_game",
                    "defensive_safeties": "defensive_safeties_per_game",
                },
            )
            + float(scoring_rules.get("defensive_blocked_kicks", 0.0)) * 0.1
            + points_allowed
            + float(scoring_rules.get("points_allowed", 0.0)) * 18.0
            + float(scoring_rules.get("yards_allowed", 0.0)) * 300.0
        ) / 8.0
    return (reception * 5 + float(scoring_rules.get("receiving_yards", 0.0)) * 50) / 14.0


def _freshness(
    features: ProjectionFeatures, parameters: ProjectionParameters, now: datetime
) -> tuple[float, tuple[str, ...]]:
    if features.source_updated_at is None:
        return 0.75, ("missing_source_timestamp",)
    if features.source_updated_at.tzinfo is None:
        raise ProjectionError("feature source timestamp must include a timezone")
    age_days = max(0.0, (now - features.source_updated_at.astimezone(UTC)).total_seconds() / 86400)
    if age_days > parameters.stale_after_days:
        return 0.65, ("stale_features",)
    return 1.0, ()


def project_player(
    player: ProjectionInput,
    scoring_rules: Mapping[str, float],
    parameters: ProjectionParameters | None = None,
    now: datetime | None = None,
) -> PlayerProjection:
    """Calculate a deterministic, independently inspectable player projection."""
    active_parameters = parameters or ProjectionParameters()
    calculation_time = now or datetime.now(UTC)
    if calculation_time.tzinfo is None:
        raise ProjectionError("projection calculation timestamp must include a timezone")
    validate_scoring_rules(scoring_rules)
    normalized = player.features.normalized()
    warnings: tuple[str, ...]
    freshness, warnings = _freshness(player.features, active_parameters, calculation_time)
    components: dict[str, float] = {}
    present = 0
    if player.is_rookie:
        assert player.rookie_prior is not None
        for name, weight in active_parameters.rookie_weights.items():
            value = player.rookie_prior.values()[name]
            # Missing rookie evidence gets a neutral prior, not a negative historical penalty.
            components[f"rookie_{name}"] = weight * (0.5 if value is None else value)
            present += value is not None
        base = sum(components.values())
        confidence = 0.45 + 0.45 * (present / len(active_parameters.rookie_weights))
        warnings = (*warnings, "rookie_prior")
    else:
        for name, weight in active_parameters.position_weights[player.position].items():
            value = normalized[name]
            if name == "availability" and value is None:
                warnings = (*warnings, "availability_unknown")
                continue
            components[name] = weight * (0.5 if value is None else value)
            present += value is not None
        supported_weight = sum(
            weight
            for name, weight in active_parameters.position_weights[player.position].items()
            if name in components
        )
        base = sum(components.values()) / supported_weight if supported_weight else 0.5
        confidence = 0.35 + 0.55 * (
            present / len(active_parameters.position_weights[player.position])
        )
        if "availability_unknown" in warnings:
            confidence *= 0.92
    scoring = _scoring_adjustment(player.position, scoring_rules, player.features)
    components["scoring_adjustment"] = scoring / 10.0
    expected = round((7.0 + 18.0 * base + scoring) * freshness, 3)
    confidence = round(_clamp(confidence * freshness), 3)
    spread = 3.0 + (1.0 - confidence) * 7.0
    return PlayerProjection(
        internal_player_id=player.internal_player_id,
        position=player.position,
        expected_points=expected,
        floor_points=round(max(0.0, expected - spread), 3),
        ceiling_points=round(expected + spread, 3),
        confidence=confidence,
        components=components,
        warnings=warnings,
        model_version=active_parameters.model_version,
        normalization_version=active_parameters.normalization_version,
    )
