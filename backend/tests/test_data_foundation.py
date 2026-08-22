from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nfl_fantasy_assistant.data.curation import (
    PLAYER_SCHEMA,
    WEEK_SCHEMA,
    curate_players,
    curate_weeks,
    validate_curated_tables,
    write_curated_parquet,
)
from nfl_fantasy_assistant.data.errors import DataValidationError, PublicationError
from nfl_fantasy_assistant.data.features import build_semantic_features
from nfl_fantasy_assistant.data.identity import (
    ExternalReference,
    IdentityPipeline,
    ManualOverride,
    Resolution,
    normalize_name,
)
from nfl_fantasy_assistant.data.ingestion import (
    RetrievedSource,
    SnapshotIngestor,
    SourceSpec,
)
from nfl_fantasy_assistant.data.preparation import (
    LeaguePreparationContext,
    prepare_baseline_pool,
    score_stat_line,
)
from nfl_fantasy_assistant.data.publishing import (
    DatasetPublisher,
    OutputFile,
    PinnedDataset,
    dataset_manifest,
)


class FixtureFetcher:
    def __init__(self, payload: bytes = b"fixture", fail: bool = False) -> None:
        self.payload = payload
        self.fail = fail

    def fetch(self, spec: SourceSpec, cache_dir: Path) -> RetrievedSource:
        if self.fail:
            raise OSError("network interrupted")
        return RetrievedSource(
            payload=self.payload,
            resolved_url="https://example.test/nflverse/players",
            source_version="fixture-v1",
            schema={"player_id": "string"},
            retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def player_row(player_id: str = "00-003", **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": player_id,
        "gsis_id": player_id,
        "display_name": "D'Andre Swift",
        "position": "RB",
        "nfl_team": "CHI",
        "source_updated_at": "2025-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def week_row(week: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "player_id": "00-003",
        "season": 2025,
        "week": week,
        "position": "RB",
        "rush_attempts": 10,
        "targets": 4,
        "receptions": 3,
        "passing_attempts": 0,
        "air_yards": 15,
        "receiving_yards": 25,
        "rushing_yards": 50,
        "passing_yards": 0,
        "touchdowns": 1,
        "red_zone_touches": 2,
        "snap_share": 0.7,
        "active": True,
        "source_updated_at": "2025-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def test_ingestion_is_idempotent_and_does_not_publish_failed_download(tmp_path: Path) -> None:
    ingestor = SnapshotIngestor(tmp_path / "raw", tmp_path / "cache")
    spec = SourceSpec("nflverse", 2025, "players", "CC BY 4.0", ("player_id",))
    first = ingestor.ingest(spec, FixtureFetcher())
    second = ingestor.ingest(spec, FixtureFetcher())
    assert first.manifest_id == second.manifest_id
    assert (tmp_path / "raw" / "nflverse" / "2025" / first.manifest_id / "manifest.json").exists()
    with pytest.raises(OSError):
        ingestor.ingest(
            SourceSpec("nflverse", 2024, "players", "CC BY 4.0", ("player_id",)),
            FixtureFetcher(fail=True),
        )
    assert (
        not list((tmp_path / "raw" / "nflverse" / "2024").glob("**/manifest.json"))
        if (tmp_path / "raw" / "nflverse" / "2024").exists()
        else True
    )


def test_curation_validates_and_writes_repeatable_parquet(tmp_path: Path) -> None:
    players = curate_players([player_row()], "source-1")
    weeks = curate_weeks([week_row(1), week_row(2)], "source-1")
    assert write_curated_parquet(players, PLAYER_SCHEMA, tmp_path / "players.parquet")
    assert write_curated_parquet(weeks, WEEK_SCHEMA, tmp_path / "weeks.parquet")
    validate_curated_tables(players, weeks, {"RB": 1})
    with pytest.raises(DataValidationError, match="unknown players"):
        validate_curated_tables(
            players, curate_weeks([week_row(1, player_id="missing")], "source-1")
        )
    with pytest.raises(DataValidationError, match="duplicate player-week"):
        curate_weeks([week_row(1), week_row(1)], "source-1")
    with pytest.raises(DataValidationError, match="snap_share"):
        curate_weeks([week_row(1, snap_share=1.1)], "source-1")
    with pytest.raises(DataValidationError, match="unsupported season/week"):
        curate_weeks([week_row(19)], "source-1")


def test_identity_exact_candidate_conflict_and_override() -> None:
    players = curate_players(
        [
            player_row("a", display_name="Marvin Jones Jr.", gsis_id="gsis-a", nfl_team="DET"),
            player_row("b", display_name="Marvin Jones", gsis_id="gsis-b", nfl_team="JAX"),
        ],
        "source-1",
    )
    pipeline = IdentityPipeline.from_players(players, "espn")
    exact = pipeline.resolve(ExternalReference("espn", "gsis-a"))
    assert exact.state == "resolved"
    assert normalize_name("D’Andre-Swift Jr.") == "dandreswift"
    assert pipeline.resolve(ExternalReference("other", None, "Marvin Jones")).state == "conflict"
    resolved = pipeline.resolve(ExternalReference("other", None, "Marvin Jones", "JAX", "RB"))
    assert resolved.state == "resolved"
    override = ManualOverride(
        "espn",
        "custom",
        exact.internal_player_id or "",
        "documented",
        "ticket",
        "2026-01-01T00:00:00+00:00",
        "old",
    )
    overridden = IdentityPipeline(players, overrides=[override]).resolve(
        ExternalReference("espn", "custom")
    )
    assert overridden.method == "manual_override"


def test_features_are_time_safe_and_retain_rookie_missingness() -> None:
    features = build_semantic_features(
        curate_weeks([week_row(1), week_row(2), week_row(3)], "source-1")
    )
    assert features[0].historical_production_points_per_game is None
    assert features[1].historical_production_points_per_game == pytest.approx(16.5)
    assert features[2].observation_cutoff == (2025, 2)
    assert features[2].usage_per_game_4 == pytest.approx(14)


def test_scoring_and_pool_reject_unsupported_or_unresolved() -> None:
    score = score_stat_line(
        {"passing_yards": 250, "passing_touchdowns": 2, "interceptions": 1},
        {"passing_yards": 0.04, "passing_touchdowns": 4, "interceptions": -2},
    )
    assert score == 16
    assert (
        score_stat_line(
            {"rushing_yards": 80, "receptions": 4}, {"rushing_yards": 0.1, "receptions": 1}
        )
        == 12
    )
    assert (
        score_stat_line(
            {"receiving_yards": 90, "receiving_touchdowns": 1},
            {"receiving_yards": 0.1, "receiving_touchdowns": 6},
        )
        == 15
    )
    assert (
        score_stat_line(
            {"receptions": 5, "receiving_yards": 40}, {"receptions": 1.5, "receiving_yards": 0.1}
        )
        == 11.5
    )
    with pytest.raises(DataValidationError, match="unsupported scoring"):
        score_stat_line({}, {"return_yards": 0.1})
    resolved = IdentityPipeline.from_players(curate_players([player_row()], "source-1")).resolve(
        ExternalReference("nflverse", "00-003")
    )
    context = LeaguePreparationContext(
        8, ("QB", "RB", "WR", "TE", "FLEX"), frozenset({"RB", "WR", "TE"})
    )
    pool = prepare_baseline_pool([(resolved, "RB", 10, "now")], "feature-1", "dataset-1", context)
    assert pool[0].internal_player_id == resolved.internal_player_id
    with pytest.raises(DataValidationError, match="unresolved"):
        prepare_baseline_pool(
            [(Resolution("unresolved", None, None, "missing ID"), "RB", 1, "now")],
            "f",
            "d",
            context,
        )
    large_pool = prepare_baseline_pool(
        [
            (
                Resolution("resolved", f"player-{index}", "fixture", "fixture"),
                "RB",
                float(index),
                "now",
            )
            for index in range(350)
        ],
        "feature-1",
        "dataset-1",
        context,
    )
    assert len(large_pool) == 300
    assert large_pool[0].baseline_score == 349


def test_publication_is_atomic_and_retains_active_version(tmp_path: Path) -> None:
    payload = b"parquet-fixture"
    output = OutputFile("prepared.parquet", hashlib.sha256(payload).hexdigest(), 1)
    valid = {name: True for name in DatasetPublisher.REQUIRED_CHECKS}
    manifest = dataset_manifest(
        "dataset-1",
        "feature-1",
        "revision-1",
        ("source-1",),
        {"prepared": "v1"},
        (output,),
        valid,
        ("CC BY 4.0",),
    )
    publisher = DatasetPublisher(tmp_path / "prepared")
    publisher.publish(manifest, {"prepared.parquet": payload}, {"prepared.parquet": 1})
    assert publisher.active_version() == ("dataset-1", "feature-1")
    invalid = dataset_manifest(
        "dataset-2",
        "feature-1",
        "revision-1",
        ("source-1",),
        {"prepared": "v1"},
        (output,),
        {"schema": False},
        ("CC BY 4.0",),
    )
    with pytest.raises(DataValidationError):
        publisher.publish(invalid, {"prepared.parquet": payload}, {"prepared.parquet": 1})
    assert publisher.active_version() == ("dataset-1", "feature-1")
    with pytest.raises(PublicationError):
        PinnedDataset("draft-1", "dataset-1", "feature-1").require_same_version(
            "dataset-2", "feature-1"
        )
