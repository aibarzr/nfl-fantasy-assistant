"""Explicit league scoring and deterministic baseline-pool preparation."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from nfl_fantasy_assistant.domain.scoring import (
    SUPPORTED_SCORING_STATS,
    ScoringError,
    validate_scoring_rules,
)

from .curation import SUPPORTED_POSITIONS
from .errors import DataValidationError
from .identity import Resolution


def validate_prepared_scoring_rules(scoring_rules: Mapping[str, float]) -> None:
    """Reject unmapped scoring semantics before they reach a draft configuration."""
    try:
        validate_scoring_rules(scoring_rules)
    except ScoringError as error:
        raise DataValidationError(str(error)) from error


@dataclass(frozen=True, slots=True)
class PreparedPlayer:
    internal_player_id: str
    position: str
    baseline_score: float
    source_updated_at: str
    feature_version: str
    dataset_version: str


PREPARED_SCHEMA = pa.schema(
    [
        ("internal_player_id", pa.string()),
        ("position", pa.string()),
        ("baseline_score", pa.float64()),
        ("source_updated_at", pa.string()),
        ("feature_version", pa.string()),
        ("dataset_version", pa.string()),
    ]
)


@dataclass(frozen=True, slots=True)
class LeaguePreparationContext:
    """The subset of league configuration that shapes a prepared draft pool."""

    team_count: int
    roster_slots: tuple[str, ...]
    flex_eligible_positions: frozenset[str]

    def __post_init__(self) -> None:
        if self.team_count < 2:
            raise DataValidationError("league team count must be at least two")
        if not self.roster_slots:
            raise DataValidationError("league roster slots are required")
        unsupported = self.flex_eligible_positions - SUPPORTED_POSITIONS
        if unsupported:
            raise DataValidationError(f"unsupported flex positions: {sorted(unsupported)}")


def score_stat_line(stat_line: Mapping[str, float], scoring_rules: Mapping[str, float]) -> float:
    validate_prepared_scoring_rules(scoring_rules)
    unknown_stats = set(stat_line) - SUPPORTED_SCORING_STATS
    if unknown_stats:
        raise DataValidationError(f"unsupported stat line fields: {sorted(unknown_stats)}")
    return sum(float(stat_line.get(stat, 0)) * weight for stat, weight in scoring_rules.items())


def prepare_baseline_pool(
    candidates: Iterable[tuple[Resolution, str, float, str]],
    feature_version: str,
    dataset_version: str,
    league_context: LeaguePreparationContext,
    target_size: int = 300,
) -> list[PreparedPlayer]:
    if target_size <= 0:
        raise DataValidationError("target pool size must be positive")
    prepared: list[PreparedPlayer] = []
    seen: set[str] = set()
    for resolution, position, score, source_updated_at in candidates:
        if resolution.state != "resolved" or resolution.internal_player_id is None:
            raise DataValidationError(f"unresolved identity: {resolution.evidence}")
        if position not in SUPPORTED_POSITIONS:
            raise DataValidationError(f"unsupported pool position: {position}")
        if position not in league_context.flex_eligible_positions and position not in {
            slot for slot in league_context.roster_slots if slot in SUPPORTED_POSITIONS
        }:
            raise DataValidationError(
                f"position is not eligible in league configuration: {position}"
            )
        if resolution.internal_player_id in seen:
            raise DataValidationError(f"duplicate internal player: {resolution.internal_player_id}")
        seen.add(resolution.internal_player_id)
        prepared.append(
            PreparedPlayer(
                internal_player_id=resolution.internal_player_id,
                position=position,
                baseline_score=float(score),
                source_updated_at=source_updated_at,
                feature_version=feature_version,
                dataset_version=dataset_version,
            )
        )
    return sorted(prepared, key=lambda player: (-player.baseline_score, player.internal_player_id))[
        :target_size
    ]


def write_prepared_parquet(rows: Iterable[PreparedPlayer], path: Path) -> str:
    """Write prepared, version-pinned values for atomic dataset publication."""
    table = pa.Table.from_pylist([asdict(row) for row in rows], schema=PREPARED_SCHEMA)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", version="2.6")
    return hashlib.sha256(path.read_bytes()).hexdigest()
