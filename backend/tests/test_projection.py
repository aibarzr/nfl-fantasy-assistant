from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from nfl_fantasy_assistant.models.metrics import projection_metrics
from nfl_fantasy_assistant.models.projection import (
    ProjectionError,
    ProjectionFeatures,
    ProjectionInput,
    ProjectionParameters,
    RookiePrior,
    project_player,
)

NOW = datetime(2026, 8, 1, tzinfo=UTC)
SCORING = {
    "passing_yards": 0.04,
    "passing_touchdowns": 4.0,
    "rushing_yards": 0.1,
    "receptions": 1.0,
    "receiving_yards": 0.1,
}


def features(**overrides: object) -> ProjectionFeatures:
    values: dict[str, Any] = {
        "usage_per_game": 18.0,
        "opportunity_per_game": 20.0,
        "efficiency_per_opportunity": 1.0,
        "high_value_usage_per_game": 2.0,
        "receiving_role": 0.6,
        "rushing_role": 0.4,
        "role_stability": 0.8,
        "availability_rate": 0.9,
        "historical_points_per_game": 16.0,
        "source_updated_at": NOW,
    }
    values.update(overrides)
    return ProjectionFeatures(**values)


@pytest.mark.parametrize("position", ("QB", "RB", "WR", "TE", "K", "DEF"))
def test_position_projectors_are_deterministic_and_position_specific(position: str) -> None:
    projection = project_player(
        ProjectionInput(f"player-{position}", position, features()), SCORING, now=NOW
    )
    replay = project_player(
        ProjectionInput(f"player-{position}", position, features()), SCORING, now=NOW
    )
    assert projection == replay
    assert projection.floor_points < projection.expected_points < projection.ceiling_points
    assert projection.model_version == "projection-v3"
    if position == "QB":
        assert "rushing_role" in projection.components
    if position in {"RB", "WR", "TE"}:
        assert "receiving_role" in projection.components
    if position == "K":
        assert "kicking_attempts" in projection.components
    if position == "DEF":
        assert "defensive_sacks" in projection.components


def test_ppr_and_stale_feature_inputs_change_scoring_and_confidence_explicitly() -> None:
    player = ProjectionInput("receiver", "WR", features())
    standard = project_player(player, {"receiving_yards": 0.1}, now=NOW)
    ppr = project_player(player, {"receiving_yards": 0.1, "receptions": 1.0}, now=NOW)
    stale = project_player(
        ProjectionInput("stale", "WR", features(source_updated_at=NOW - timedelta(days=15))),
        SCORING,
        now=NOW,
    )
    assert ppr.expected_points > standard.expected_points
    assert stale.confidence < ppr.confidence
    assert "stale_features" in stale.warnings


def test_rookie_uses_documented_prior_without_missing_history_penalty() -> None:
    rookie = project_player(
        ProjectionInput(
            "rookie",
            "RB",
            ProjectionFeatures(source_updated_at=NOW),
            is_rookie=True,
            rookie_prior=RookiePrior(ecr_rank=20, draft_capital_score=0.8, expected_role_score=0.7),
        ),
        SCORING,
        now=NOW,
    )
    assert rookie.expected_points > 0
    assert "rookie_ecr" in rookie.components
    assert "rookie_prior" in rookie.warnings
    assert rookie.confidence > 0.45
    with pytest.raises(ProjectionError, match="rookie prior"):
        ProjectionInput("bad-rookie", "RB", features(), is_rookie=True)
    with pytest.raises(ProjectionError, match="team-defense"):
        ProjectionInput(
            "bad-defense", "DEF", features(), is_rookie=True, rookie_prior=RookiePrior()
        )


def test_kicker_and_defense_scoring_are_explicit_and_position_specific() -> None:
    kicker = ProjectionInput(
        "kicker-1",
        "K",
        features(
            kicking_attempts_per_game=3.0,
            kicking_conversion_rate=0.9,
            extra_point_attempts_per_game=2.0,
        ),
    )
    defense = ProjectionInput(
        "defense-1",
        "DEF",
        features(
            defensive_sacks_per_game=3.0,
            turnovers_forced_per_game=1.5,
            points_allowed_per_game=18.0,
        ),
    )
    scored_kicker = project_player(kicker, {"field_goals_made": 3.0}, now=NOW)
    scored_defense = project_player(defense, {"defensive_sacks": 1.0}, now=NOW)
    assert scored_kicker.expected_points > project_player(kicker, {}, now=NOW).expected_points
    assert scored_defense.expected_points > project_player(defense, {}, now=NOW).expected_points


def test_banded_kicker_and_defense_scoring_uses_curated_rates_or_fails_closed() -> None:
    kicker = ProjectionInput(
        "banded-kicker",
        "K",
        features(
            field_goals_made_0_19_per_game=0.5,
            field_goals_made_20_29_per_game=0.5,
            field_goals_made_30_39_per_game=0.5,
            field_goals_made_40_49_per_game=0.5,
            field_goals_made_50_plus_per_game=1.0,
            field_goals_missed_0_19_per_game=0.25,
            field_goals_missed_20_29_per_game=0.0,
            field_goals_missed_30_39_per_game=0.25,
            extra_points_made_per_game=2.0,
            extra_points_missed_per_game=0.25,
        ),
    )
    scoring = {
        "field_goals_made_0_19": 3.0,
        "field_goals_made_20_29": 3.0,
        "field_goals_made_30_39": 3.0,
        "field_goals_made_40_49": 3.0,
        "field_goals_made_50_plus": 5.0,
        "field_goals_missed_0_19": -1.0,
        "field_goals_missed_20_29": -1.0,
        "field_goals_missed_30_39": -1.0,
        "extra_points_made": 1.0,
        "extra_points_missed": -1.5,
    }
    scored = project_player(kicker, scoring, now=NOW)
    assert scored.expected_points > project_player(kicker, {}, now=NOW).expected_points
    with pytest.raises(ProjectionError, match="complete curated feature coverage"):
        project_player(
            ProjectionInput("missing-band", "K", features()),
            {"field_goals_made_50_plus": 5.0},
            now=NOW,
        )

    defense = ProjectionInput(
        "banded-defense",
        "DEF",
        features(
            defensive_sacks_per_game=2.0,
            defensive_interceptions_per_game=1.0,
            defensive_fumble_recoveries_per_game=0.5,
            defensive_touchdowns_per_game=0.25,
            defensive_safeties_per_game=0.25,
            defensive_points_allowed_0_rate=0.25,
            defensive_points_allowed_1_6_rate=0.25,
            defensive_points_allowed_7_13_rate=0.25,
            defensive_points_allowed_14_20_rate=0.25,
            defensive_points_allowed_21_27_rate=0.0,
            defensive_points_allowed_28_34_rate=0.0,
            defensive_points_allowed_35_plus_rate=0.0,
        ),
    )
    defense_scoring = {
        "defensive_sacks": 1.0,
        "defensive_interceptions": 2.0,
        "defensive_fumble_recoveries": 2.0,
        "defensive_touchdowns": 6.0,
        "defensive_safeties": 2.0,
        "defensive_points_allowed_0": 10.0,
        "defensive_points_allowed_1_6": 7.0,
        "defensive_points_allowed_7_13": 4.0,
        "defensive_points_allowed_14_20": 1.0,
        "defensive_points_allowed_21_27": 0.0,
        "defensive_points_allowed_28_34": -1.0,
        "defensive_points_allowed_35_plus": -4.0,
    }
    assert (
        project_player(defense, defense_scoring, now=NOW).expected_points
        > project_player(defense, {}, now=NOW).expected_points
    )
    with pytest.raises(ProjectionError, match="complete curated feature coverage"):
        project_player(
            ProjectionInput("missing-points-band", "DEF", features()),
            {"defensive_points_allowed_0": 10.0},
            now=NOW,
        )


def test_parameter_validation_and_timezone_requirements_are_visible() -> None:
    with pytest.raises(ProjectionError, match="sum to one"):
        ProjectionParameters(rookie_weights={"ecr": 1.0, "draft_capital": 1.0})
    with pytest.raises(ProjectionError, match="timezone"):
        project_player(
            ProjectionInput("naive", "WR", features(source_updated_at=datetime(2026, 8, 1))),
            SCORING,
            now=NOW,
        )


def test_projection_metrics_are_deterministic_and_segmented_by_position() -> None:
    metrics = projection_metrics((("QB", 20.0, 18.0), ("QB", 10.0, 12.0), ("RB", 15.0, 14.0)))
    assert metrics.count == 3
    assert metrics.mae == pytest.approx(1.666667)
    assert metrics.by_position["QB"].spearman == pytest.approx(1.0)
    k_def_metrics = projection_metrics((("K", 12.0, 11.0), ("DEF", 9.0, 10.0)))
    assert set(k_def_metrics.by_position) == {"K", "DEF"}
