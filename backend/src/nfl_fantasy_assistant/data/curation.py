"""Deterministic conversion of source-shaped rows into stable football tables."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from .errors import DataValidationError

SCHEMA_VERSION = "1"
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


@dataclass(frozen=True, slots=True)
class CuratedPlayer:
    source_player_id: str
    gsis_id: str | None
    display_name: str
    position: str
    nfl_team: str | None
    source_updated_at: str
    lineage_manifest_id: str


@dataclass(frozen=True, slots=True)
class CuratedWeek:
    source_player_id: str
    season: int
    week: int
    position: str
    rush_attempts: float | None
    targets: float | None
    receptions: float | None
    passing_attempts: float | None
    air_yards: float | None
    receiving_yards: float | None
    rushing_yards: float | None
    passing_yards: float | None
    touchdowns: float | None
    red_zone_touches: float | None
    snap_share: float | None
    active: bool
    source_updated_at: str
    lineage_manifest_id: str


PLAYER_SCHEMA = pa.schema(
    [
        ("source_player_id", pa.string()),
        ("gsis_id", pa.string()),
        ("display_name", pa.string()),
        ("position", pa.string()),
        ("nfl_team", pa.string()),
        ("source_updated_at", pa.string()),
        ("lineage_manifest_id", pa.string()),
    ]
)
WEEK_SCHEMA = pa.schema(
    [
        ("source_player_id", pa.string()),
        ("season", pa.int16()),
        ("week", pa.int8()),
        ("position", pa.string()),
        *[
            (name, pa.float64())
            for name in CuratedWeek.__dataclass_fields__
            if name
            not in {
                "source_player_id",
                "season",
                "week",
                "position",
                "active",
                "source_updated_at",
                "lineage_manifest_id",
            }
        ],
        ("active", pa.bool_()),
        ("source_updated_at", pa.string()),
        ("lineage_manifest_id", pa.string()),
    ]
)


def _required(row: Mapping[str, Any], name: str) -> Any:
    value = row.get(name)
    if value is None or value == "":
        raise DataValidationError(f"missing required source field: {name}")
    return value


def _number(row: Mapping[str, Any], name: str) -> float | None:
    value = row.get(name)
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise DataValidationError(f"{name} must be numeric") from error
    if number < 0:
        raise DataValidationError(f"{name} cannot be negative")
    return number


def curate_players(rows: Iterable[Mapping[str, Any]], manifest_id: str) -> list[CuratedPlayer]:
    result: list[CuratedPlayer] = []
    seen: set[str] = set()
    for row in rows:
        source_player_id = str(_required(row, "player_id"))
        if source_player_id in seen:
            raise DataValidationError(f"duplicate player key: {source_player_id}")
        seen.add(source_player_id)
        position = str(_required(row, "position")).upper()
        if position not in SUPPORTED_POSITIONS:
            raise DataValidationError(f"unsupported player position: {position}")
        result.append(
            CuratedPlayer(
                source_player_id=source_player_id,
                gsis_id=str(row["gsis_id"]) if row.get("gsis_id") else None,
                display_name=str(_required(row, "display_name")),
                position=position,
                nfl_team=str(row["nfl_team"]).upper() if row.get("nfl_team") else None,
                source_updated_at=str(_required(row, "source_updated_at")),
                lineage_manifest_id=manifest_id,
            )
        )
    return sorted(result, key=lambda player: player.source_player_id)


def curate_weeks(rows: Iterable[Mapping[str, Any]], manifest_id: str) -> list[CuratedWeek]:
    result: list[CuratedWeek] = []
    seen: set[tuple[str, int, int]] = set()
    numeric_fields = tuple(
        name
        for name in CuratedWeek.__dataclass_fields__
        if name
        not in {
            "source_player_id",
            "season",
            "week",
            "position",
            "active",
            "source_updated_at",
            "lineage_manifest_id",
        }
    )
    for row in rows:
        key = (
            str(_required(row, "player_id")),
            int(_required(row, "season")),
            int(_required(row, "week")),
        )
        if key in seen:
            raise DataValidationError(f"duplicate player-week key: {key}")
        if key[1] not in range(2022, 2026) or key[2] not in range(1, 19):
            raise DataValidationError(f"unsupported season/week: {key[1:]}")
        seen.add(key)
        position = str(_required(row, "position")).upper()
        if position not in SUPPORTED_POSITIONS:
            raise DataValidationError(f"unsupported player position: {position}")
        values = {field: _number(row, field) for field in numeric_fields}
        snap_share = values["snap_share"]
        if snap_share is not None and snap_share > 1:
            raise DataValidationError("snap_share must be within [0, 1]")
        result.append(
            CuratedWeek(
                source_player_id=key[0],
                season=key[1],
                week=key[2],
                position=position,
                active=bool(_required(row, "active")),
                source_updated_at=str(_required(row, "source_updated_at")),
                lineage_manifest_id=manifest_id,
                **values,
            )
        )
    return sorted(result, key=lambda week: (week.season, week.week, week.source_player_id))


def validate_curated_tables(
    players: Iterable[CuratedPlayer],
    weeks: Iterable[CuratedWeek],
    minimum_rows_by_position: Mapping[str, int] | None = None,
) -> None:
    """Run publication-facing referential and expected-coverage checks."""

    player_rows = tuple(players)
    week_rows = tuple(weeks)
    player_ids = {player.source_player_id for player in player_rows}
    if len(player_ids) != len(player_rows):
        raise DataValidationError("players table has non-unique source_player_id values")
    unknown = sorted({week.source_player_id for week in week_rows} - player_ids)
    if unknown:
        raise DataValidationError(f"player-week rows reference unknown players: {unknown}")
    if minimum_rows_by_position:
        observed = {position: 0 for position in minimum_rows_by_position}
        for player in player_rows:
            if player.position in observed:
                observed[player.position] += 1
        missing = {
            position: required
            for position, required in minimum_rows_by_position.items()
            if observed.get(position, 0) < required
        }
        if missing:
            raise DataValidationError(f"unexpected position coverage: {missing}")


def write_curated_parquet(
    rows: Iterable[CuratedPlayer | CuratedWeek], schema: pa.Schema, path: Path
) -> str:
    materialized = [asdict(row) for row in rows]
    table = pa.Table.from_pylist(materialized, schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", version="2.6")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_contract() -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "players": {field.name: str(field.type) for field in PLAYER_SCHEMA},
        "player_week_features": {field.name: str(field.type) for field in WEEK_SCHEMA},
        "key_semantics": {
            "players": ["source_player_id"],
            "player_week_features": ["source_player_id", "season", "week"],
        },
        "null_semantics": "null means unavailable at the source; zero is observed zero.",
        "units": {"snap_share": "fraction", "yards": "yards", "counts": "events"},
    }


def write_table_contract(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(table_contract(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
