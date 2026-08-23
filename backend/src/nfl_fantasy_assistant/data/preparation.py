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
from .publishing import DatasetManifest, read_published_dataset_manifest


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


@dataclass(frozen=True, slots=True)
class PreparedRecommendationInput:
    """Offline model outputs retained for a prepared asset's runtime draft ranking.

    These fields are deliberately the narrow, typed values used by dynamic VOR and ranking. They
    are not raw nflverse records, provider catalog data, or an alternative runtime projector.
    """

    internal_player_id: str
    position: str
    expected_points: float
    floor_points: float
    ceiling_points: float
    projection_confidence: float
    projection_warnings: tuple[str, ...]
    projection_model_version: str
    projection_normalization_version: str
    value_score: float
    value_confidence: float
    value_uncertainty: float
    market_prior: float
    value_warnings: tuple[str, ...]
    value_version: str
    value_normalization_version: str
    source_updated_at: str
    feature_version: str
    dataset_version: str


@dataclass(frozen=True, slots=True)
class PublishedPreparedPool:
    """A prepared pool proven to be an output of one immutable dataset version."""

    players: tuple[PreparedPlayer, ...]
    checksum_sha256: str
    dataset_version: str
    feature_version: str
    manifest: DatasetManifest


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


PREPARED_RECOMMENDATION_INPUT_SCHEMA = pa.schema(
    [
        ("internal_player_id", pa.string()),
        ("position", pa.string()),
        ("expected_points", pa.float64()),
        ("floor_points", pa.float64()),
        ("ceiling_points", pa.float64()),
        ("projection_confidence", pa.float64()),
        ("projection_warnings", pa.list_(pa.string())),
        ("projection_model_version", pa.string()),
        ("projection_normalization_version", pa.string()),
        ("value_score", pa.float64()),
        ("value_confidence", pa.float64()),
        ("value_uncertainty", pa.float64()),
        ("market_prior", pa.float64()),
        ("value_warnings", pa.list_(pa.string())),
        ("value_version", pa.string()),
        ("value_normalization_version", pa.string()),
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


def read_prepared_parquet(path: Path) -> tuple[PreparedPlayer, ...]:
    """Load a published prepared-pool artifact with its typed identity boundary intact."""
    table = pq.read_table(path)
    if table.schema != PREPARED_SCHEMA:
        raise DataValidationError("prepared player table does not match the required schema")
    rows = tuple(PreparedPlayer(**row) for row in table.to_pylist())
    if len({row.internal_player_id for row in rows}) != len(rows):
        raise DataValidationError("prepared player table contains duplicate internal IDs")
    return rows


def write_prepared_recommendation_inputs_parquet(
    rows: Iterable[PreparedRecommendationInput], path: Path
) -> str:
    """Write the immutable ranking inputs selected with the prepared pool."""
    table = pa.Table.from_pylist(
        [asdict(row) for row in rows], schema=PREPARED_RECOMMENDATION_INPUT_SCHEMA
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", version="2.6")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_prepared_recommendation_inputs_parquet(
    path: Path,
) -> tuple[PreparedRecommendationInput, ...]:
    """Load typed ranking inputs while rejecting schema or identity drift."""
    table = pq.read_table(path)
    if table.schema != PREPARED_RECOMMENDATION_INPUT_SCHEMA:
        raise DataValidationError("prepared recommendation input table has an unexpected schema")
    rows_list: list[PreparedRecommendationInput] = []
    for row in table.to_pylist():
        projection_warnings = row["projection_warnings"]
        value_warnings = row["value_warnings"]
        if not isinstance(projection_warnings, list) or not isinstance(value_warnings, list):
            raise DataValidationError("prepared recommendation input warnings must be lists")
        rows_list.append(
            PreparedRecommendationInput(
                **{
                    **row,
                    "projection_warnings": tuple(projection_warnings),
                    "value_warnings": tuple(value_warnings),
                }
            )
        )
    rows = tuple(rows_list)
    if len({row.internal_player_id for row in rows}) != len(rows):
        raise DataValidationError(
            "prepared recommendation input table contains duplicate internal IDs"
        )
    return rows


def read_published_prepared_pool(version: Path) -> PublishedPreparedPool:
    """Read the prepared output of a checksum-verified immutable dataset version."""
    manifest = read_published_dataset_manifest(version)
    outputs = [output for output in manifest.outputs if output.relative_path == "prepared.parquet"]
    if len(outputs) != 1:
        raise DataValidationError(
            "published dataset must declare exactly one prepared.parquet output"
        )
    output = outputs[0]
    path = version / output.relative_path
    players = read_prepared_parquet(path)
    if len(players) != output.row_count:
        raise DataValidationError("prepared player row count does not match dataset manifest")
    if any(
        player.dataset_version != manifest.dataset_version
        or player.feature_version != manifest.feature_version
        for player in players
    ):
        raise DataValidationError("prepared player versions do not match dataset manifest")
    return PublishedPreparedPool(
        players=players,
        checksum_sha256=output.checksum_sha256,
        dataset_version=manifest.dataset_version,
        feature_version=manifest.feature_version,
        manifest=manifest,
    )
