from __future__ import annotations

import hashlib
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
import pytest

from nfl_fantasy_assistant.data.errors import DataValidationError
from nfl_fantasy_assistant.data.preparation import (
    PreparedPlayer,
    PreparedRecommendationInput,
    write_prepared_parquet,
    write_prepared_recommendation_inputs_parquet,
)
from nfl_fantasy_assistant.data.publishing import DatasetPublisher, OutputFile, dataset_manifest
from nfl_fantasy_assistant.data.runtime import activate_sleeper_dataset
from nfl_fantasy_assistant.data.sleeper_identity import (
    SLEEPER_COVERAGE_SCHEMA,
    SLEEPER_EXTERNAL_ID_SCHEMA,
)


def parquet_bytes(rows: list[dict[str, object]], schema: pa.Schema) -> bytes:
    sink = pa.BufferOutputStream()
    pq.write_table(
        pa.Table.from_pylist(rows, schema=schema), sink, compression="zstd", version="2.6"
    )
    return bytes(sink.getvalue().to_pybytes())


def published_dataset(
    root: Path, *, valid_coverage: bool = True, include_recommendation_inputs: bool = False
) -> Path:
    version_name = "sleeper-runtime-fixture-v1"
    prepared = (
        PreparedPlayer(
            "player-fixture", "QB", 10.0, "2026-08-23T00:00:00+00:00", "3", version_name
        ),
        PreparedPlayer(
            "defense-fixture", "DEF", 8.0, "2026-08-23T00:00:00+00:00", "3", version_name
        ),
    )
    temporary = root / "prepared-tmp.parquet"
    write_prepared_parquet(prepared, temporary)
    prepared_bytes = temporary.read_bytes()
    temporary.unlink()
    mappings = parquet_bytes(
        [
            {
                "provider": "sleeper",
                "external_id": "player-external",
                "internal_player_id": "player-fixture",
                "asset_type": "player",
                "resolution_method": "fixture",
                "provenance": "fixture",
                "validity_state": "resolved",
                "season": 2026,
            },
            {
                "provider": "sleeper",
                "external_id": "DET",
                "internal_player_id": "defense-fixture",
                "asset_type": "team_defense",
                "resolution_method": "fixture",
                "provenance": "fixture",
                "validity_state": "resolved",
                "season": 2026,
            },
        ],
        SLEEPER_EXTERNAL_ID_SCHEMA,
    )
    coverage = parquet_bytes(
        [
            {
                "provider": "sleeper",
                "season": 2026,
                "position": position,
                "catalog_total": 1,
                "catalog_resolved": 1,
                "catalog_blocked": 0,
                "prepared_total": 1,
                "prepared_resolved": 1 if valid_coverage else 0,
                "prepared_blocked": 0 if valid_coverage else 1,
            }
            for position in ("QB", "DEF")
        ],
        SLEEPER_COVERAGE_SCHEMA,
    )
    files = {
        "prepared.parquet": prepared_bytes,
        "asset_external_ids.parquet": mappings,
        "sleeper_crosswalk_coverage.parquet": coverage,
    }
    if include_recommendation_inputs:
        input_path = root / "recommendation-inputs.parquet"
        write_prepared_recommendation_inputs_parquet(
            (
                PreparedRecommendationInput(
                    "player-fixture",
                    "QB",
                    20.0,
                    14.0,
                    26.0,
                    0.8,
                    (),
                    "projection-v3",
                    "semantic-v3",
                    0.8,
                    0.8,
                    0.1,
                    0.7,
                    (),
                    "value-v1",
                    "value-minmax-v1",
                    "2026-08-23T00:00:00+00:00",
                    "3",
                    version_name,
                ),
                PreparedRecommendationInput(
                    "defense-fixture",
                    "DEF",
                    10.0,
                    7.0,
                    13.0,
                    0.7,
                    ("fixture_warning",),
                    "projection-v3",
                    "semantic-v3",
                    0.4,
                    0.7,
                    0.2,
                    0.3,
                    (),
                    "value-v1",
                    "value-minmax-v1",
                    "2026-08-23T00:00:00+00:00",
                    "3",
                    version_name,
                ),
            ),
            input_path,
        )
        files["prepared_recommendation_inputs.parquet"] = input_path.read_bytes()
        input_path.unlink()
    outputs = tuple(
        OutputFile(name, hashlib.sha256(payload).hexdigest(), 2)
        for name, payload in sorted(files.items())
    )
    manifest = dataset_manifest(
        version_name,
        "3",
        "fixture-runtime-v1",
        ("fixture-source",),
        {
            "prepared": "v2",
            "asset_external_ids": "sleeper-v1",
            "sleeper_crosswalk_coverage": "v1",
        },
        outputs,
        {name: True for name in DatasetPublisher.REQUIRED_CHECKS},
        ("fixture",),
    )
    return DatasetPublisher(root).publish(manifest, files, {name: 2 for name in files})


def test_runtime_activation_loads_only_exact_prepared_sleeper_assets(tmp_path: Path) -> None:
    activated = activate_sleeper_dataset(published_dataset(tmp_path / "prepared"))

    assert activated.dataset_version == "sleeper-runtime-fixture-v1"
    assert activated.feature_version == "3"
    assert activated.model_version == "projection-v3"
    assert {player.external_ids["sleeper"] for player in activated.players} == {
        "player-external",
        "DET",
    }
    defense = next(player for player in activated.players if player.position == "DEF")
    assert defense.nfl_team == "DET"
    assert all(player.display_name == player.internal_player_id for player in activated.players)
    assert activated.recommendations_ready is False


def test_runtime_activation_loads_only_validated_recommendation_inputs(tmp_path: Path) -> None:
    activated = activate_sleeper_dataset(
        published_dataset(tmp_path / "prepared", include_recommendation_inputs=True)
    )

    assert activated.recommendations_ready is True
    assert {item.internal_player_id for item in activated.recommendation_inputs} == {
        "player-fixture",
        "defense-fixture",
    }
    assert activated.recommendation_inputs[1].value.components == {"market_prior": 0.7}


def test_runtime_activation_rejects_bad_coverage_and_changed_outputs(tmp_path: Path) -> None:
    with pytest.raises(DataValidationError, match="coverage"):
        activate_sleeper_dataset(published_dataset(tmp_path / "invalid", valid_coverage=False))

    version = published_dataset(tmp_path / "changed")
    (version / "prepared.parquet").write_bytes(b"changed")
    with pytest.raises(DataValidationError, match="checksum"):
        activate_sleeper_dataset(version)
