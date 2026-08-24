"""Time-safe semantic feature construction over curated player-week records."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .curation import CuratedWeek
from .durability import DurabilityFeature
from .errors import DataValidationError

FEATURE_VERSION = "4"


@dataclass(frozen=True, slots=True)
class SemanticFeature:
    source_player_id: str
    season: int
    week: int
    observation_cutoff: tuple[int, int]
    usage_per_game_4: float | None
    opportunity_per_game_4: float | None
    efficiency_per_opportunity_4: float | None
    high_value_usage_per_game_4: float | None
    role_stability_4: float | None
    availability_rate_4: float | None
    durability_rate_4: float | None
    durability_rate_8: float | None
    prior_season_participation_rate: float | None
    multi_season_durability: float | None
    historical_production_points_per_game: float | None
    kicking_attempts_per_game_4: float | None
    kicking_conversion_rate_4: float | None
    extra_point_attempts_per_game_4: float | None
    extra_points_made_per_game_4: float | None
    extra_points_missed_per_game_4: float | None
    field_goals_made_0_19_per_game_4: float | None
    field_goals_made_20_29_per_game_4: float | None
    field_goals_made_30_39_per_game_4: float | None
    field_goals_made_40_49_per_game_4: float | None
    field_goals_made_50_plus_per_game_4: float | None
    field_goals_missed_0_19_per_game_4: float | None
    field_goals_missed_20_29_per_game_4: float | None
    field_goals_missed_30_39_per_game_4: float | None
    field_goals_missed_40_49_per_game_4: float | None
    field_goals_missed_50_plus_per_game_4: float | None
    defensive_sacks_per_game_4: float | None
    defensive_interceptions_per_game_4: float | None
    defensive_fumble_recoveries_per_game_4: float | None
    defensive_safeties_per_game_4: float | None
    turnovers_forced_per_game_4: float | None
    points_allowed_per_game_4: float | None
    defensive_touchdowns_per_game_4: float | None
    defensive_points_allowed_0_rate_4: float | None
    defensive_points_allowed_1_6_rate_4: float | None
    defensive_points_allowed_7_13_rate_4: float | None
    defensive_points_allowed_14_20_rate_4: float | None
    defensive_points_allowed_21_27_rate_4: float | None
    defensive_points_allowed_28_34_rate_4: float | None
    defensive_points_allowed_35_plus_rate_4: float | None
    feature_version: str
    lineage_manifest_ids: tuple[str, ...]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _period(row: CuratedWeek) -> tuple[int, int]:
    return row.season, row.week


def _fantasy_production(row: CuratedWeek) -> float:
    # This is historical production represented once; downstream projectors must not add its
    # component stats as a second final-score input.
    skill_position_points = (
        (row.receptions or 0)
        + (row.receiving_yards or 0) / 10
        + (row.rushing_yards or 0) / 10
        + (row.passing_yards or 0) / 25
        + (row.touchdowns or 0) * 6
    )
    if row.position == "K":
        return (row.field_goals_made or 0) * 3 + (row.extra_points_made or 0)
    if row.position == "DEF":
        return (
            (row.defensive_sacks or 0)
            + (row.defensive_interceptions or 0) * 2
            + (row.defensive_fumble_recoveries or 0) * 2
            + (row.defensive_touchdowns or 0) * 6
        )
    return skill_position_points


def build_semantic_features(
    rows: Iterable[CuratedWeek],
    durability_features: Iterable[DurabilityFeature] = (),
) -> list[SemanticFeature]:
    """Build each row using only earlier player weeks, including prior seasons."""

    ordered = sorted(rows, key=lambda row: (row.source_player_id, row.season, row.week))
    durability_rows = tuple(durability_features)
    durability_by_key = {
        (item.source_player_id, item.season, item.week): item for item in durability_rows
    }
    if len(durability_by_key) != len(durability_rows):
        raise DataValidationError("duplicate durability feature key")
    seen: set[tuple[str, int, int]] = set()
    by_player: dict[str, list[CuratedWeek]] = {}
    result: list[SemanticFeature] = []
    for row in ordered:
        key = (row.source_player_id, row.season, row.week)
        if key in seen:
            raise DataValidationError(f"duplicate feature key: {key}")
        seen.add(key)
        history = by_player.setdefault(row.source_player_id, [])[-4:]
        usage = [(item.targets or 0) + (item.rush_attempts or 0) for item in history]
        opportunity = [
            (item.targets or 0) + (item.rush_attempts or 0) + (item.red_zone_touches or 0)
            for item in history
        ]
        kicking_attempts = [item.field_goal_attempts or 0 for item in history]
        kicking_attempts_made = [item.field_goals_made or 0 for item in history]
        extra_point_attempts = [item.extra_point_attempts or 0 for item in history]
        extra_points_made = [
            item.extra_points_made for item in history if item.extra_points_made is not None
        ]
        extra_points_missed = [
            item.extra_points_missed for item in history if item.extra_points_missed is not None
        ]
        defensive_sacks = [item.defensive_sacks or 0 for item in history]
        turnovers_forced = [
            (item.defensive_interceptions or 0) + (item.defensive_fumble_recoveries or 0)
            for item in history
        ]
        points_allowed = [
            item.points_allowed for item in history if item.points_allowed is not None
        ]
        defensive_touchdowns = [item.defensive_touchdowns or 0 for item in history]
        yards = [(item.receiving_yards or 0) + (item.rushing_yards or 0) for item in history]
        opportunities = [(item.targets or 0) + (item.rush_attempts or 0) for item in history]
        efficiency_values = [
            yard / chance for yard, chance in zip(yards, opportunities, strict=True) if chance > 0
        ]
        snap_shares = [item.snap_share for item in history if item.snap_share is not None]
        stability = None
        if len(snap_shares) >= 2:
            mean = sum(snap_shares) / len(snap_shares)
            stability = 1 - min(
                1.0, sum(abs(value - mean) for value in snap_shares) / len(snap_shares)
            )
        result.append(
            SemanticFeature(
                source_player_id=row.source_player_id,
                season=row.season,
                week=row.week,
                observation_cutoff=(row.season, row.week - 1),
                usage_per_game_4=_mean(usage),
                opportunity_per_game_4=_mean(opportunity),
                efficiency_per_opportunity_4=_mean(efficiency_values),
                high_value_usage_per_game_4=_mean([item.red_zone_touches or 0 for item in history]),
                role_stability_4=stability,
                availability_rate_4=_mean(
                    [1.0 if item.active else 0.0 for item in history if item.active is not None]
                ),
                durability_rate_4=(
                    durability.durability_rate_4
                    if (durability := durability_by_key.get(key)) is not None
                    else None
                ),
                durability_rate_8=(
                    durability.durability_rate_8 if durability is not None else None
                ),
                prior_season_participation_rate=(
                    durability.prior_season_participation_rate if durability is not None else None
                ),
                multi_season_durability=(
                    durability.multi_season_durability if durability is not None else None
                ),
                historical_production_points_per_game=_mean(
                    [_fantasy_production(item) for item in history]
                ),
                kicking_attempts_per_game_4=_mean(kicking_attempts),
                kicking_conversion_rate_4=(
                    sum(kicking_attempts_made) / sum(kicking_attempts)
                    if sum(kicking_attempts) > 0
                    else None
                ),
                extra_point_attempts_per_game_4=_mean(extra_point_attempts),
                extra_points_made_per_game_4=_mean(extra_points_made),
                extra_points_missed_per_game_4=_mean(extra_points_missed),
                **{
                    f"field_goals_made_{band}_per_game_4": _mean(
                        [
                            getattr(item, f"field_goals_made_{band}")
                            for item in history
                            if getattr(item, f"field_goals_made_{band}") is not None
                        ]
                    )
                    for band in ("0_19", "20_29", "30_39", "40_49", "50_plus")
                },
                **{
                    f"field_goals_missed_{band}_per_game_4": _mean(
                        [
                            getattr(item, f"field_goals_missed_{band}")
                            for item in history
                            if getattr(item, f"field_goals_missed_{band}") is not None
                        ]
                    )
                    for band in ("0_19", "20_29", "30_39", "40_49", "50_plus")
                },
                defensive_sacks_per_game_4=_mean(defensive_sacks),
                defensive_interceptions_per_game_4=_mean(
                    [item.defensive_interceptions or 0 for item in history]
                ),
                defensive_fumble_recoveries_per_game_4=_mean(
                    [item.defensive_fumble_recoveries or 0 for item in history]
                ),
                defensive_safeties_per_game_4=_mean(
                    [item.defensive_safeties or 0 for item in history]
                ),
                turnovers_forced_per_game_4=_mean(turnovers_forced),
                points_allowed_per_game_4=_mean(points_allowed),
                defensive_touchdowns_per_game_4=_mean(defensive_touchdowns),
                **{
                    f"defensive_points_allowed_{band}_rate_4": _mean(
                        [
                            getattr(item, f"defensive_points_allowed_{band}")
                            for item in history
                            if getattr(item, f"defensive_points_allowed_{band}") is not None
                        ]
                    )
                    for band in ("0", "1_6", "7_13", "14_20", "21_27", "28_34", "35_plus")
                },
                feature_version=FEATURE_VERSION,
                lineage_manifest_ids=tuple(sorted({item.lineage_manifest_id for item in history})),
            )
        )
        by_player[row.source_player_id].append(row)
    return result
