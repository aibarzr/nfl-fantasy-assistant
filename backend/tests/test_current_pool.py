from __future__ import annotations

import hashlib
import json
from dataclasses import fields
from pathlib import Path
from typing import Any, cast

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from nfl_fantasy_assistant.data.curation import CuratedPlayer, CuratedWeek
from nfl_fantasy_assistant.data.current_pool import (
    LocalLeagueConfiguration,
    VerifiedSnapshot,
    build_current_prepared_pool,
    publish_current_prepared_pool,
    read_verified_snapshot,
)
from nfl_fantasy_assistant.data.errors import DataValidationError
from nfl_fantasy_assistant.data.identity import internal_player_id
from nfl_fantasy_assistant.data.preparation import read_published_prepared_pool

NOW = "2026-08-23T00:00:00+00:00"


def player() -> CuratedPlayer:
    return CuratedPlayer(
        "player-1",
        "player-1",
        "espn-1",
        "Fixture Back",
        "RB",
        "AAA",
        "player",
        None,
        None,
        NOW,
        "players-manifest",
    )


def week(number: int) -> CuratedWeek:
    values: dict[str, object] = {
        field.name: None
        for field in fields(CuratedWeek)
        if field.name
        not in {
            "source_player_id",
            "season",
            "week",
            "position",
            "active",
            "source_updated_at",
            "lineage_manifest_id",
        }
    }
    values.update({"rush_attempts": 10.0, "targets": 3.0, "receptions": 2.0, "rushing_yards": 50.0})
    return CuratedWeek(
        "player-1",
        2025,
        number,
        "RB",
        active=True,
        source_updated_at=NOW,
        lineage_manifest_id="stats-manifest",
        **cast(Any, values),
    )


def roster_snapshot() -> VerifiedSnapshot:
    return VerifiedSnapshot(
        "rosters-manifest",
        "rosters",
        2026,
        NOW,
        "CC BY 4.0",
        ({"gsis_id": "player-1", "position": "RB"},),
    )


def league() -> LocalLeagueConfiguration:
    return LocalLeagueConfiguration(8, ("RB",), frozenset(), {"receptions": 1.0})


def test_current_pool_is_scored_only_for_current_crosswalk_assets() -> None:
    prepared = build_current_prepared_pool(
        (player(),),
        tuple(week(number) for number in range(1, 6)),
        roster_snapshot(),
        frozenset({internal_player_id(player())}),
        league(),
        dataset_version="fixture-current-v1",
        target_size=1,
    )

    assert len(prepared) == 1
    assert prepared[0].internal_player_id == internal_player_id(player())
    assert prepared[0].feature_version == "3"
    assert prepared[0].dataset_version == "fixture-current-v1"


def test_current_pool_fails_when_no_current_asset_has_a_crosswalk() -> None:
    with pytest.raises(DataValidationError, match="no current crosswalk-resolved"):
        build_current_prepared_pool(
            (player(),),
            tuple(week(number) for number in range(1, 6)),
            roster_snapshot(),
            frozenset(),
            league(),
            dataset_version="fixture-current-v1",
        )


def test_published_current_pool_is_a_checksum_verified_immutable_version(tmp_path: Path) -> None:
    prepared = build_current_prepared_pool(
        (player(),),
        tuple(week(number) for number in range(1, 6)),
        roster_snapshot(),
        frozenset({internal_player_id(player())}),
        league(),
        dataset_version="fixture-current-v1",
        target_size=1,
    )

    version = publish_current_prepared_pool(
        prepared, (roster_snapshot(),), tmp_path / "prepared", dataset_version="fixture-current-v1"
    )

    published = read_published_prepared_pool(version)
    assert published.players == prepared
    assert published.manifest.source_manifest_ids == ("rosters-manifest",)


def test_source_snapshot_rejects_a_checksum_mismatch(tmp_path: Path) -> None:
    snapshot = tmp_path / "snapshot.parquet"
    pq.write_table(pa.table({"player_id": ["fixture"]}), snapshot)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_id": "fixture-manifest",
                "dataset": "player_stats",
                "season": 2025,
                "checksum_sha256": hashlib.sha256(b"wrong").hexdigest(),
                "retrieved_at": NOW,
                "license_note": "CC BY 4.0",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(DataValidationError, match="checksum"):
        read_verified_snapshot(manifest, snapshot)
