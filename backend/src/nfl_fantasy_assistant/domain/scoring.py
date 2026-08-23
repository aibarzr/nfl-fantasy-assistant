"""Versioned, neutral fantasy-scoring semantics owned by the domain boundary."""

from __future__ import annotations

from collections.abc import Mapping


class ScoringError(ValueError):
    """A league scoring rule cannot be represented safely by the supported codebook."""


SCORING_CODEBOOK_VERSION = "semantic-v3"
FIELD_GOAL_MADE_BANDS = frozenset(
    {
        "field_goals_made_0_19",
        "field_goals_made_20_29",
        "field_goals_made_30_39",
        "field_goals_made_40_49",
        "field_goals_made_50_plus",
    }
)
FIELD_GOAL_MISSED_BANDS = frozenset(
    {
        "field_goals_missed_0_19",
        "field_goals_missed_20_29",
        "field_goals_missed_30_39",
        "field_goals_missed_40_49",
        "field_goals_missed_50_plus",
    }
)
DEFENSIVE_POINTS_ALLOWED_BANDS = frozenset(
    {
        "defensive_points_allowed_0",
        "defensive_points_allowed_1_6",
        "defensive_points_allowed_7_13",
        "defensive_points_allowed_14_20",
        "defensive_points_allowed_21_27",
        "defensive_points_allowed_28_34",
        "defensive_points_allowed_35_plus",
    }
)
SUPPORTED_SCORING_STATS = frozenset(
    {
        "passing_yards",
        "passing_touchdowns",
        "interceptions",
        "rushing_yards",
        "rushing_touchdowns",
        "receptions",
        "receiving_yards",
        "receiving_touchdowns",
        "fumbles_lost",
        "field_goals_made",
        "field_goals_missed",
        "field_goals_made_0_19",
        "field_goals_made_20_29",
        "field_goals_made_30_39",
        "field_goals_made_40_49",
        "field_goals_made_50_plus",
        "field_goals_missed_0_19",
        "field_goals_missed_20_29",
        "field_goals_missed_30_39",
        "field_goals_missed_40_49",
        "field_goals_missed_50_plus",
        "extra_points_made",
        "extra_points_missed",
        "defensive_sacks",
        "defensive_interceptions",
        "defensive_fumble_recoveries",
        "defensive_touchdowns",
        "defensive_safeties",
        "defensive_blocked_kicks",
        "points_allowed",
        "yards_allowed",
        "defensive_points_allowed_0",
        "defensive_points_allowed_1_6",
        "defensive_points_allowed_7_13",
        "defensive_points_allowed_14_20",
        "defensive_points_allowed_21_27",
        "defensive_points_allowed_28_34",
        "defensive_points_allowed_35_plus",
    }
)


def validate_scoring_rules(scoring_rules: Mapping[str, float]) -> None:
    """Reject unmapped semantic scoring rules before canonical state is created."""
    unsupported = set(scoring_rules) - SUPPORTED_SCORING_STATS
    if unsupported:
        raise ScoringError(f"unsupported scoring semantics: {sorted(unsupported)}")
    for flat_rule, bands in (
        ("field_goals_made", FIELD_GOAL_MADE_BANDS),
        ("field_goals_missed", FIELD_GOAL_MISSED_BANDS),
        ("points_allowed", DEFENSIVE_POINTS_ALLOWED_BANDS),
    ):
        if flat_rule in scoring_rules and bands & scoring_rules.keys():
            raise ScoringError(
                f"{flat_rule} cannot be combined with its mutually exclusive band rules"
            )
