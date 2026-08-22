"""Time-safe deterministic backtests and explicit model-promotion gates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from .metrics import ProjectionMetrics, projection_metrics


class BacktestError(ValueError):
    """A backtest is leaky, incomplete, or cannot be reproduced."""


BASELINE_STRATEGIES = frozenset(
    {"ecr_only", "adp_only", "best_available", "static_vor", "dynamic_vor", "full_engine"}
)


@dataclass(frozen=True, slots=True)
class ProjectionObservation:
    position: str
    predicted_points: float
    actual_points: float
    feature_cutoff: datetime
    decision_at: datetime


@dataclass(frozen=True, slots=True)
class DecisionObservation:
    decision_id: str
    decision_at: datetime
    feature_cutoff: datetime
    actual_values: Mapping[str, float]
    strategy_rankings: Mapping[str, tuple[str, ...]]
    position: str
    stage: str
    slot: int
    is_rookie: bool
    confidence_bucket: str


@dataclass(frozen=True, slots=True)
class StrategyMetrics:
    decisions: int
    mean_top_pick_value: float
    mean_top_n_value: float
    by_position: Mapping[str, float]
    by_stage: Mapping[str, float]
    by_slot: Mapping[int, float]
    by_rookie: Mapping[bool, float]
    by_confidence: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class BacktestReport:
    dataset_version: str
    feature_version: str
    model_version: str
    parameter_version: str
    transform_revision: str
    projection: ProjectionMetrics
    strategies: Mapping[str, StrategyMetrics]
    limitations: tuple[str, ...]


def _require_time_safe(feature_cutoff: datetime, decision_at: datetime) -> None:
    if feature_cutoff.tzinfo is None or decision_at.tzinfo is None:
        raise BacktestError("backtest timestamps must include timezones")
    if feature_cutoff > decision_at:
        raise BacktestError("backtest feature cutoff cannot be later than decision point")


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _segmented[Segment](values: list[tuple[Segment, float]]) -> dict[Segment, float]:
    grouped: dict[Segment, list[float]] = {}
    for segment, value in values:
        grouped.setdefault(segment, []).append(value)
    return {
        key: _mean(items) for key, items in sorted(grouped.items(), key=lambda item: str(item[0]))
    }


def run_backtest(
    projections: tuple[ProjectionObservation, ...],
    decisions: tuple[DecisionObservation, ...],
    *,
    dataset_version: str,
    feature_version: str,
    model_version: str,
    parameter_version: str,
    transform_revision: str,
    limitations: tuple[str, ...],
    top_n: int = 3,
) -> BacktestReport:
    """Evaluate time-safe projections and declared baseline/full-engine decision strategies."""
    if not all(
        (dataset_version, feature_version, model_version, parameter_version, transform_revision)
    ):
        raise BacktestError("backtest reports must pin all data/model/parameter versions")
    if top_n < 1 or not limitations:
        raise BacktestError("backtests require a positive Top-N and recorded limitations")
    for row in projections:
        _require_time_safe(row.feature_cutoff, row.decision_at)
    for decision in decisions:
        _require_time_safe(decision.feature_cutoff, decision.decision_at)
        if set(decision.strategy_rankings) != BASELINE_STRATEGIES:
            raise BacktestError("each decision must contain every declared baseline strategy")
        if not decision.actual_values:
            raise BacktestError("decision outcomes require actual player values")
        for strategy, ranking in decision.strategy_rankings.items():
            if not ranking or any(
                identifier not in decision.actual_values for identifier in ranking
            ):
                raise BacktestError(
                    f"strategy {strategy} ranks a player absent from actual outcomes"
                )
    projection_report = projection_metrics(
        (row.position, row.predicted_points, row.actual_points) for row in projections
    )
    strategy_reports: dict[str, StrategyMetrics] = {}
    for strategy in sorted(BASELINE_STRATEGIES):
        rows: list[tuple[DecisionObservation, float, float]] = []
        for decision in decisions:
            ranking = decision.strategy_rankings[strategy]
            top = decision.actual_values[ranking[0]]
            top_n_value = _mean([decision.actual_values[player] for player in ranking[:top_n]])
            rows.append((decision, top, top_n_value))
        strategy_reports[strategy] = StrategyMetrics(
            decisions=len(rows),
            mean_top_pick_value=_mean([row[1] for row in rows]),
            mean_top_n_value=_mean([row[2] for row in rows]),
            by_position=_segmented([(row[0].position, row[1]) for row in rows]),
            by_stage=_segmented([(row[0].stage, row[1]) for row in rows]),
            by_slot=_segmented([(row[0].slot, row[1]) for row in rows]),
            by_rookie=_segmented([(row[0].is_rookie, row[1]) for row in rows]),
            by_confidence=_segmented([(row[0].confidence_bucket, row[1]) for row in rows]),
        )
    return BacktestReport(
        dataset_version,
        feature_version,
        model_version,
        parameter_version,
        transform_revision,
        projection_report,
        strategy_reports,
        limitations,
    )


def assert_promotable(
    candidate: BacktestReport,
    baseline: BacktestReport,
    *,
    maximum_segment_regression: float = 0.1,
) -> None:
    """Block promotion unless reproducible full-engine evidence beats the declared baseline."""
    if (
        candidate.dataset_version != baseline.dataset_version
        or candidate.feature_version != baseline.feature_version
    ):
        raise BacktestError(
            "promotion comparison requires the same pinned data and feature versions"
        )
    candidate_full = candidate.strategies["full_engine"]
    baseline_full = baseline.strategies["full_engine"]
    if candidate_full.mean_top_pick_value <= baseline_full.mean_top_pick_value:
        raise BacktestError("promotion requires primary top-pick metric improvement")
    _assert_no_segment_regression(
        "position",
        candidate_full.by_position,
        baseline_full.by_position,
        maximum_segment_regression,
    )
    _assert_no_segment_regression(
        "stage",
        candidate_full.by_stage,
        baseline_full.by_stage,
        maximum_segment_regression,
    )
    _assert_no_segment_regression(
        "slot",
        candidate_full.by_slot,
        baseline_full.by_slot,
        maximum_segment_regression,
    )
    _assert_no_segment_regression(
        "rookie",
        candidate_full.by_rookie,
        baseline_full.by_rookie,
        maximum_segment_regression,
    )
    _assert_no_segment_regression(
        "confidence",
        candidate_full.by_confidence,
        baseline_full.by_confidence,
        maximum_segment_regression,
    )


def _assert_no_segment_regression[Segment](
    name: str,
    candidate_segments: Mapping[Segment, float],
    baseline_segments: Mapping[Segment, float],
    maximum_segment_regression: float,
) -> None:
    for segment, baseline_value in baseline_segments.items():
        candidate_value = candidate_segments.get(segment)
        if candidate_value is None or candidate_value < baseline_value - maximum_segment_regression:
            raise BacktestError(f"promotion has an unacceptable {name} segment regression")
