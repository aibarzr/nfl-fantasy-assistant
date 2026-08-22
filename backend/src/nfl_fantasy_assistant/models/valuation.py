"""Context-independent player valuation with an explicit market prior and uncertainty."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from .projection import PlayerProjection


class ValuationError(ValueError):
    """A valuation input cannot be reproduced safely."""


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize(values: Mapping[str, float]) -> dict[str, float]:
    if not values:
        return {}
    lower, upper = min(values.values()), max(values.values())
    if lower == upper:
        return {identifier: 0.5 for identifier in values}
    return {identifier: (value - lower) / (upper - lower) for identifier, value in values.items()}


@dataclass(frozen=True, slots=True)
class MarketPrior:
    """Permitted market observation; rank/ADP is never conflated with player identity."""

    ecr_rank: float | None = None
    adp: float | None = None
    best_rank: float | None = None
    worst_rank: float | None = None
    rank_movement: float | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        if any(value is not None and value <= 0 for value in (self.ecr_rank, self.adp)):
            raise ValuationError("market ECR rank and ADP must be positive")
        if self.updated_at is not None and self.updated_at.tzinfo is None:
            raise ValuationError("market timestamp must include a timezone")

    @property
    def ranking(self) -> float | None:
        return self.ecr_rank if self.ecr_rank is not None else self.adp


@dataclass(frozen=True, slots=True)
class ValueInput:
    projection: PlayerProjection
    market: MarketPrior | None = None


@dataclass(frozen=True, slots=True)
class ValuationParameters:
    value_version: str = "value-v1"
    normalization_version: str = "value-minmax-v1"
    own_model_weight: float = 0.65
    market_weight: float = 0.35
    stale_after_days: int = 7
    stale_market_weight_factor: float = 0.4
    missing_market_confidence_penalty: float = 0.15

    def __post_init__(self) -> None:
        if not self.value_version or not self.normalization_version or self.stale_after_days < 1:
            raise ValuationError("valuation requires versions and positive freshness policy")
        if abs(self.own_model_weight + self.market_weight - 1.0) > 0.000001:
            raise ValuationError("own-model and market weights must sum to one")
        if (
            not 0 <= self.stale_market_weight_factor <= 1
            or not 0 <= self.missing_market_confidence_penalty <= 1
        ):
            raise ValuationError("valuation confidence parameters must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class PlayerValue:
    internal_player_id: str
    position: str
    value_score: float
    confidence: float
    uncertainty: float
    components: Mapping[str, float]
    warnings: tuple[str, ...]
    value_version: str
    normalization_version: str


def _market_freshness(
    prior: MarketPrior | None, parameters: ValuationParameters, now: datetime
) -> tuple[float, float, tuple[str, ...]]:
    """Return effective market weight, confidence modifier, and explicit warnings."""
    if prior is None or prior.ranking is None:
        return 0.0, 1.0 - parameters.missing_market_confidence_penalty, ("missing_market",)
    if prior.updated_at is None:
        return parameters.market_weight, 0.9, ("missing_market_timestamp",)
    age = (now - prior.updated_at.astimezone(UTC)).total_seconds() / 86400
    if age > parameters.stale_after_days:
        return (
            parameters.market_weight * parameters.stale_market_weight_factor,
            0.8,
            ("stale_market",),
        )
    return parameters.market_weight, 1.0, ()


def value_players(
    inputs: Iterable[ValueInput],
    parameters: ValuationParameters | None = None,
    now: datetime | None = None,
) -> tuple[PlayerValue, ...]:
    """Value a batch deterministically without introducing draft context or historical rows."""
    active_parameters = parameters or ValuationParameters()
    materialized = tuple(inputs)
    if not materialized:
        return ()
    if len({item.projection.internal_player_id for item in materialized}) != len(materialized):
        raise ValuationError("value inputs require unique internal player IDs")
    calculation_time = now or datetime.now(UTC)
    if calculation_time.tzinfo is None:
        raise ValuationError("valuation calculation timestamp must include a timezone")
    projection_scores = _normalize(
        {
            item.projection.internal_player_id: item.projection.expected_points
            for item in materialized
        }
    )
    rankings = {
        item.projection.internal_player_id: item.market.ranking
        for item in materialized
        if item.market is not None and item.market.ranking is not None
    }
    # A lower ECR/ADP rank is a stronger market signal.
    market_scores = {identifier: 1.0 - value for identifier, value in _normalize(rankings).items()}
    values: list[PlayerValue] = []
    for item in materialized:
        identifier = item.projection.internal_player_id
        effective_market_weight, freshness_confidence, warnings = _market_freshness(
            item.market, active_parameters, calculation_time
        )
        own_weight = 1.0 - effective_market_weight
        own_score = projection_scores[identifier]
        market_score = market_scores.get(identifier, own_score)
        prior = item.market
        dispersion = 0.0
        movement = 0.0
        if prior is not None:
            if prior.best_rank is not None and prior.worst_rank is not None:
                dispersion = _clamp(abs(prior.worst_rank - prior.best_rank) / 100.0)
            if prior.rank_movement is not None:
                movement = _clamp(abs(prior.rank_movement) / 50.0)
        uncertainty = round(
            _clamp(dispersion * 0.6 + movement * 0.4 + (1 - freshness_confidence)), 3
        )
        confidence = round(
            _clamp(item.projection.confidence * freshness_confidence * (1.0 - uncertainty * 0.35)),
            3,
        )
        values.append(
            PlayerValue(
                internal_player_id=identifier,
                position=item.projection.position,
                value_score=round(
                    own_weight * own_score + effective_market_weight * market_score, 6
                ),
                confidence=confidence,
                uncertainty=uncertainty,
                components={
                    "own_model": own_score,
                    "market_prior": market_score,
                    "own_model_weight": own_weight,
                    "market_weight": effective_market_weight,
                    "market_dispersion": dispersion,
                    "market_movement": movement,
                },
                warnings=warnings,
                value_version=active_parameters.value_version,
                normalization_version=active_parameters.normalization_version,
            )
        )
    return tuple(sorted(values, key=lambda item: (-item.value_score, item.internal_player_id)))
