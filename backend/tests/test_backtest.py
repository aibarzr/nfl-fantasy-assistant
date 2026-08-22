from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from nfl_fantasy_assistant.models.backtest import (
    BacktestError,
    BacktestReport,
    DecisionObservation,
    ProjectionObservation,
    assert_promotable,
    run_backtest,
)

NOW = datetime(2026, 8, 1, tzinfo=UTC)


def decision(full_order: tuple[str, ...] = ("a", "b", "c")) -> DecisionObservation:
    rankings = {
        "ecr_only": ("b", "a", "c"),
        "adp_only": ("b", "a", "c"),
        "best_available": ("a", "b", "c"),
        "static_vor": ("a", "b", "c"),
        "dynamic_vor": ("a", "b", "c"),
        "full_engine": full_order,
    }
    return DecisionObservation(
        "decision-1",
        NOW,
        NOW - timedelta(days=1),
        {"a": 20, "b": 10, "c": 5},
        rankings,
        "RB",
        "early",
        1,
        False,
        "high",
    )


def report(full_order: tuple[str, ...] = ("a", "b", "c")) -> BacktestReport:
    return run_backtest(
        (ProjectionObservation("RB", 15, 16, NOW - timedelta(days=1), NOW),),
        (decision(full_order),),
        dataset_version="dataset-v1",
        feature_version="feature-v1",
        model_version="model-v1",
        parameter_version="parameters-v1",
        transform_revision="transform-v1",
        limitations=("synthetic fixture",),
    )


def test_backtest_is_time_safe_segmented_and_reproducible() -> None:
    first = report()
    assert first == report()
    assert first.projection.by_position["RB"].mae == 1
    assert first.strategies["full_engine"].mean_top_pick_value == 20
    assert first.strategies["full_engine"].by_stage["early"] == 20


def test_backtest_rejects_leakage_and_missing_declared_baseline() -> None:
    with pytest.raises(BacktestError, match="cutoff"):
        run_backtest(
            (ProjectionObservation("RB", 1, 1, NOW + timedelta(seconds=1), NOW),),
            (decision(),),
            dataset_version="d",
            feature_version="f",
            model_version="m",
            parameter_version="p",
            transform_revision="t",
            limitations=("fixture",),
        )
    broken = decision()
    with pytest.raises(BacktestError, match="every declared"):
        run_backtest(
            (ProjectionObservation("RB", 1, 1, NOW, NOW),),
            (
                DecisionObservation(
                    broken.decision_id,
                    broken.decision_at,
                    broken.feature_cutoff,
                    broken.actual_values,
                    {"full_engine": broken.strategy_rankings["full_engine"]},
                    broken.position,
                    broken.stage,
                    broken.slot,
                    broken.is_rookie,
                    broken.confidence_bucket,
                ),
            ),
            dataset_version="d",
            feature_version="f",
            model_version="m",
            parameter_version="p",
            transform_revision="t",
            limitations=("fixture",),
        )


def test_promotion_requires_improvement_and_blocks_segment_regression() -> None:
    baseline = report(("b", "a", "c"))
    candidate = report(("a", "b", "c"))
    assert_promotable(candidate, baseline)
    with pytest.raises(BacktestError, match="improvement"):
        assert_promotable(baseline, candidate)

    degraded_full = replace(candidate.strategies["full_engine"], by_stage={"early": 0.0})
    degraded = replace(
        candidate,
        strategies={**candidate.strategies, "full_engine": degraded_full},
    )
    with pytest.raises(BacktestError, match="stage segment"):
        assert_promotable(degraded, baseline)


def test_k_and_def_segments_are_present_in_reproducible_promotion_evidence() -> None:
    def observation(position: str, first: str) -> DecisionObservation:
        rankings = {
            strategy: (first, "b", "c")
            for strategy in {
                "ecr_only",
                "adp_only",
                "best_available",
                "static_vor",
                "dynamic_vor",
                "full_engine",
            }
        }
        return DecisionObservation(
            f"decision-{position}",
            NOW,
            NOW - timedelta(days=1),
            {"a": 12, "b": 8, "c": 4},
            rankings,
            position,
            "late",
            1,
            False,
            "medium",
        )

    def k_def_report(first: str) -> BacktestReport:
        return run_backtest(
            (
                ProjectionObservation("K", 10, 11, NOW - timedelta(days=1), NOW),
                ProjectionObservation("DEF", 9, 10, NOW - timedelta(days=1), NOW),
            ),
            (observation("K", first), observation("DEF", first)),
            dataset_version="k-def-fixture-v1",
            feature_version="feature-v2",
            model_version="projection-v2",
            parameter_version="parameters-v2",
            transform_revision="k-def-pbp-v1",
            limitations=("synthetic K/DEF fixture",),
        )

    baseline = k_def_report("b")
    candidate = k_def_report("a")
    assert candidate == k_def_report("a")
    assert set(candidate.projection.by_position) == {"K", "DEF"}
    assert_promotable(candidate, baseline)
