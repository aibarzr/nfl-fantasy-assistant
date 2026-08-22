"""Versioned, neutral fantasy-scoring semantics owned by the domain boundary."""

from __future__ import annotations

from collections.abc import Mapping


class ScoringError(ValueError):
    """A league scoring rule cannot be represented safely by the supported codebook."""


SCORING_CODEBOOK_VERSION = "semantic-v2"
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
    }
)


def validate_scoring_rules(scoring_rules: Mapping[str, float]) -> None:
    """Reject unmapped semantic scoring rules before canonical state is created."""
    unsupported = set(scoring_rules) - SUPPORTED_SCORING_STATS
    if unsupported:
        raise ScoringError(f"unsupported scoring semantics: {sorted(unsupported)}")
