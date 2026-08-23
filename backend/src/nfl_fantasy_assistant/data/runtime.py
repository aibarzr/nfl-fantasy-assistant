"""Activation of one immutable Sleeper prepared dataset for the local draft runtime."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from nfl_fantasy_assistant.domain.draft import Player
from nfl_fantasy_assistant.models.projection import ProjectionParameters

from .errors import DataValidationError
from .preparation import PreparedPlayer, PublishedPreparedPool, read_published_prepared_pool
from .sleeper_identity import SLEEPER_COVERAGE_SCHEMA, SLEEPER_EXTERNAL_ID_SCHEMA


@dataclass(frozen=True, slots=True)
class ActivatedSleeperDataset:
    """Validated runtime facts, intentionally narrower than source/preparation records."""

    dataset_version: str
    feature_version: str
    model_version: str
    players: tuple[Player, ...]
    prepared_count: int


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
    return ActivatedSleeperDataset(
        published.dataset_version,
        published.feature_version,
        ProjectionParameters().model_version,
        players,
        len(published.players),
    )
