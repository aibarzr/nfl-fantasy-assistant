"""Dependency-free deterministic metrics for projection and ranking evaluation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import sqrt


class MetricsError(ValueError):
    """An evaluation cannot be calculated from the supplied paired observations."""


@dataclass(frozen=True, slots=True)
class ProjectionMetrics:
    count: int
    mae: float
    rmse: float
    spearman: float
    by_position: Mapping[str, ProjectionMetrics]


def _ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    result = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        rank = (start + 1 + end) / 2
        for index, _ in ordered[start:end]:
            result[index] = rank
        start = end
    return result


def _spearman(predicted: list[float], actual: list[float]) -> float:
    if len(predicted) < 2:
        return 0.0
    left = _ranks(predicted)
    right = _ranks(actual)
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True))
    left_variance = sum((item - left_mean) ** 2 for item in left)
    right_variance = sum((item - right_mean) ** 2 for item in right)
    if left_variance == 0 or right_variance == 0:
        return 0.0
    return numerator / sqrt(left_variance * right_variance)


def projection_metrics(rows: Iterable[tuple[str, float, float]]) -> ProjectionMetrics:
    """Calculate MAE/RMSE/Spearman overall and by position from time-safe paired outcomes."""
    materialized = tuple(rows)
    if not materialized:
        raise MetricsError("projection metrics require at least one paired outcome")
    predicted = [row[1] for row in materialized]
    actual = [row[2] for row in materialized]
    errors = [abs(left - right) for left, right in zip(predicted, actual, strict=True)]
    by_position_rows: dict[str, list[tuple[str, float, float]]] = {}
    for row in materialized:
        by_position_rows.setdefault(row[0], []).append(row)
    return ProjectionMetrics(
        count=len(materialized),
        mae=round(sum(errors) / len(errors), 6),
        rmse=round(sqrt(sum(error**2 for error in errors) / len(errors)), 6),
        spearman=round(_spearman(predicted, actual), 6),
        by_position={
            position: projection_metrics_without_segments(position_rows)
            for position, position_rows in sorted(by_position_rows.items())
        },
    )


def projection_metrics_without_segments(
    rows: Iterable[tuple[str, float, float]],
) -> ProjectionMetrics:
    """Calculate one segment without recursively creating redundant segment maps."""
    materialized = tuple(rows)
    predicted = [row[1] for row in materialized]
    actual = [row[2] for row in materialized]
    errors = [abs(left - right) for left, right in zip(predicted, actual, strict=True)]
    return ProjectionMetrics(
        count=len(materialized),
        mae=round(sum(errors) / len(errors), 6),
        rmse=round(sqrt(sum(error**2 for error in errors) / len(errors)), 6),
        spearman=round(_spearman(predicted, actual), 6),
        by_position={},
    )
