"""Time-safe semantic feature construction over curated player-week records."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .curation import CuratedWeek
from .errors import DataValidationError

FEATURE_VERSION = "1"


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
    historical_production_points_per_game: float | None
    feature_version: str
    lineage_manifest_ids: tuple[str, ...]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _period(row: CuratedWeek) -> tuple[int, int]:
    return row.season, row.week


def _fantasy_production(row: CuratedWeek) -> float:
    # This is historical production represented once; downstream projectors must not add its
    # component stats as a second final-score input.
    return (
        (row.receptions or 0)
        + (row.receiving_yards or 0) / 10
        + (row.rushing_yards or 0) / 10
        + (row.passing_yards or 0) / 25
        + (row.touchdowns or 0) * 6
    )


def build_semantic_features(rows: Iterable[CuratedWeek]) -> list[SemanticFeature]:
    """Build each row using only earlier player weeks, including prior seasons."""

    ordered = sorted(rows, key=lambda row: (row.source_player_id, row.season, row.week))
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
                availability_rate_4=_mean([1.0 if item.active else 0.0 for item in history]),
                historical_production_points_per_game=_mean(
                    [_fantasy_production(item) for item in history]
                ),
                feature_version=FEATURE_VERSION,
                lineage_manifest_ids=tuple(sorted({item.lineage_manifest_id for item in history})),
            )
        )
        by_player[row.source_player_id].append(row)
    return result
