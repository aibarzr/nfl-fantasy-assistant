"""Activation of one immutable Sleeper prepared dataset for the local draft runtime."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from nfl_fantasy_assistant.domain.draft import Player
from nfl_fantasy_assistant.models.projection import PlayerProjection, ProjectionParameters
from nfl_fantasy_assistant.models.valuation import PlayerValue

from .errors import DataValidationError
from .preparation import (
    PreparedPlayer,
    PreparedRecommendationInput,
    PublishedPreparedPool,
    read_prepared_recommendation_inputs_parquet,
    read_published_prepared_pool,
)
from .sleeper_identity import SLEEPER_COVERAGE_SCHEMA, SLEEPER_EXTERNAL_ID_SCHEMA


@dataclass(frozen=True, slots=True)
class ActivatedSleeperDataset:
    """Validated runtime facts, intentionally narrower than source/preparation records."""

    dataset_version: str
    feature_version: str
    model_version: str
    players: tuple[Player, ...]
    prepared_count: int
    recommendation_inputs: tuple[RuntimeRecommendationInput, ...] = ()

    @property
    def recommendations_ready(self) -> bool:
        return bool(self.recommendation_inputs)


@dataclass(frozen=True, slots=True)
class RuntimeRecommendationInput:
    """Validated projection/value facts used only to rank current canonical availability."""

    internal_player_id: str
    position: str
    projection: PlayerProjection
    value: PlayerValue
    source_updated_at: str


def _finite_unit(value: object, label: str) -> None:
    if not isinstance(value, int | float) or not isfinite(value) or not 0 <= value <= 1:
        raise DataValidationError(f"runtime recommendation input has an invalid {label}")


def _runtime_recommendation_inputs(
    prepared: tuple[PreparedPlayer, ...], path: Path, model_version: str
) -> tuple[RuntimeRecommendationInput, ...]:
    rows: tuple[PreparedRecommendationInput, ...] = read_prepared_recommendation_inputs_parquet(
        path
    )
    prepared_by_id = {player.internal_player_id: player for player in prepared}
    if {row.internal_player_id for row in rows} != set(prepared_by_id):
        raise DataValidationError("runtime recommendation inputs do not cover the prepared pool")
    inputs: list[RuntimeRecommendationInput] = []
    for row in rows:
        prepared_player = prepared_by_id[row.internal_player_id]
        if (
            row.position != prepared_player.position
            or row.source_updated_at != prepared_player.source_updated_at
            or row.dataset_version != prepared_player.dataset_version
            or row.feature_version != prepared_player.feature_version
            or row.projection_model_version != model_version
        ):
            raise DataValidationError(
                "runtime recommendation input conflicts with prepared provenance"
            )
        scoring_values = (
            row.expected_points,
            row.floor_points,
            row.ceiling_points,
            row.value_score,
            row.value_uncertainty,
            row.market_prior,
        )
        if (
            not all(isinstance(value, int | float) and isfinite(value) for value in scoring_values)
            or row.floor_points > row.expected_points
            or row.expected_points > row.ceiling_points
        ):
            raise DataValidationError("runtime recommendation input has invalid scoring values")
        for value, label in (
            (row.projection_confidence, "projection confidence"),
            (row.value_confidence, "value confidence"),
            (row.value_uncertainty, "value uncertainty"),
            (row.market_prior, "market prior"),
        ):
            _finite_unit(value, label)
        if not all(
            isinstance(warning, str) for warning in (*row.projection_warnings, *row.value_warnings)
        ) or not all(
            (
                row.projection_normalization_version,
                row.value_version,
                row.value_normalization_version,
            )
        ):
            raise DataValidationError(
                "runtime recommendation input has incomplete model provenance"
            )
        inputs.append(
            RuntimeRecommendationInput(
                row.internal_player_id,
                row.position,
                PlayerProjection(
                    row.internal_player_id,
                    row.position,
                    row.expected_points,
                    row.floor_points,
                    row.ceiling_points,
                    row.projection_confidence,
                    {},
                    row.projection_warnings,
                    row.projection_model_version,
                    row.projection_normalization_version,
                ),
                PlayerValue(
                    row.internal_player_id,
                    row.position,
                    row.value_score,
                    row.value_confidence,
                    row.value_uncertainty,
                    {"market_prior": row.market_prior},
                    row.value_warnings,
                    row.value_version,
                    row.value_normalization_version,
                ),
                row.source_updated_at,
            )
        )
    return tuple(sorted(inputs, key=lambda item: item.internal_player_id))


def _read_exact_table(path: Path, expected_schema: object, label: str) -> list[dict[str, object]]:
    try:
        table = pq.read_table(path)
    except (OSError, ValueError) as error:
        raise DataValidationError(f"runtime {label} output is unreadable") from error
    if table.schema != expected_schema:
        raise DataValidationError(f"runtime {label} output has an unexpected schema")
    return list(table.to_pylist())


def _validate_coverage(prepared: tuple[PreparedPlayer, ...], rows: list[dict[str, object]]) -> None:
    expected = Counter(player.position for player in prepared)
    covered: dict[str, dict[str, object]] = {}
    for row in rows:
        if row.get("provider") != "sleeper" or not isinstance(row.get("position"), str):
            raise DataValidationError(
                "runtime crosswalk coverage has an invalid provider or position"
            )
        position = row.get("position")
        assert isinstance(position, str)
        if position in covered:
            raise DataValidationError("runtime crosswalk coverage has duplicate positions")
        covered[position] = row
    for position, count in expected.items():
        coverage = covered.get(position)
        if coverage is None or (
            coverage.get("prepared_total"),
            coverage.get("prepared_resolved"),
            coverage.get("prepared_blocked"),
        ) != (count, count, 0):
            raise DataValidationError("runtime crosswalk coverage does not cover the prepared pool")


def _runtime_players(
    prepared: tuple[PreparedPlayer, ...], mappings: list[dict[str, object]]
) -> tuple[Player, ...]:
    by_internal_id: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for mapping in mappings:
        internal_id = mapping.get("internal_player_id")
        external_id = mapping.get("external_id")
        if (
            mapping.get("provider") != "sleeper"
            or mapping.get("validity_state") != "resolved"
            or not isinstance(internal_id, str)
            or not isinstance(external_id, str)
            or not internal_id
            or not external_id
        ):
            continue
        by_internal_id[internal_id].append(mapping)
    players: list[Player] = []
    for prepared_player in prepared:
        matches = by_internal_id.get(prepared_player.internal_player_id, [])
        if len(matches) != 1:
            raise DataValidationError("runtime prepared asset lacks one exact Sleeper mapping")
        mapping = matches[0]
        expected_asset_type = "team_defense" if prepared_player.position == "DEF" else "player"
        if mapping.get("asset_type") != expected_asset_type:
            raise DataValidationError(
                "runtime Sleeper mapping asset type conflicts with prepared asset"
            )
        external_id = mapping.get("external_id")
        assert isinstance(external_id, str)
        nfl_team: str | None = None
        if prepared_player.position == "DEF":
            if not external_id.isalpha() or not 2 <= len(external_id) <= 4:
                raise DataValidationError("runtime DEF mapping lacks an exact team-code identity")
            nfl_team = external_id.upper()
        players.append(
            Player(
                prepared_player.internal_player_id,
                {"sleeper": external_id},
                prepared_player.internal_player_id,
                prepared_player.position,
                nfl_team,
            )
        )
    if len({player.internal_player_id for player in players}) != len(players):
        raise DataValidationError("runtime prepared pool contains duplicate internal assets")
    if len({player.external_ids["sleeper"] for player in players}) != len(players):
        raise DataValidationError("runtime prepared pool contains duplicate Sleeper IDs")
    return tuple(sorted(players, key=lambda player: player.internal_player_id))


def activate_sleeper_dataset(version: Path) -> ActivatedSleeperDataset:
    """Validate one crosswalk-published dataset and expose only runtime-safe identity facts."""
    published: PublishedPreparedPool = read_published_prepared_pool(version)
    output_names = {output.relative_path for output in published.manifest.outputs}
    required = {
        "prepared.parquet",
        "asset_external_ids.parquet",
        "sleeper_crosswalk_coverage.parquet",
    }
    if not required <= output_names:
        raise DataValidationError("runtime dataset lacks published Sleeper identity outputs")
    mappings = _read_exact_table(
        version / "asset_external_ids.parquet", SLEEPER_EXTERNAL_ID_SCHEMA, "external IDs"
    )
    coverage = _read_exact_table(
        version / "sleeper_crosswalk_coverage.parquet", SLEEPER_COVERAGE_SCHEMA, "coverage"
    )
    _validate_coverage(published.players, coverage)
    players = _runtime_players(published.players, mappings)
    model_version = ProjectionParameters().model_version
    recommendation_inputs: tuple[RuntimeRecommendationInput, ...] = ()
    if "prepared_recommendation_inputs.parquet" in output_names:
        recommendation_outputs = [
            output
            for output in published.manifest.outputs
            if output.relative_path == "prepared_recommendation_inputs.parquet"
        ]
        if len(recommendation_outputs) != 1:
            raise DataValidationError(
                "runtime dataset has an ambiguous recommendation input output"
            )
        recommendation_inputs = _runtime_recommendation_inputs(
            published.players,
            version / "prepared_recommendation_inputs.parquet",
            model_version,
        )
        if len(recommendation_inputs) != recommendation_outputs[0].row_count:
            raise DataValidationError(
                "runtime recommendation input row count does not match dataset manifest"
            )
    return ActivatedSleeperDataset(
        published.dataset_version,
        published.feature_version,
        model_version,
        players,
        len(published.players),
        recommendation_inputs,
    )
