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
    IdentityMapping,
    IdentityPipeline,
    ManualOverride,
    Resolution,
    internal_player_id,
    normalize_name,
)
from nfl_fantasy_assistant.data.ingestion import (
    RetrievedSource,
    SleeperCatalogFetcher,
    SnapshotIngestor,
    SourceSpec,
)
from nfl_fantasy_assistant.data.k_def import (
    build_season_team_defense_assets,
    transform_pbp_k_def,
)
from nfl_fantasy_assistant.data.preparation import (
    LeaguePreparationContext,
    PreparedPlayer,
    PreparedRecommendationInput,
    prepare_baseline_pool,
    read_prepared_parquet,
    read_prepared_recommendation_inputs_parquet,
    read_published_prepared_pool,
    score_stat_line,
    write_prepared_parquet,
    write_prepared_recommendation_inputs_parquet,
)
from nfl_fantasy_assistant.data.publishing import (
    DatasetPublisher,
    OutputFile,
    PinnedDataset,
    dataset_manifest,
)
from nfl_fantasy_assistant.data.sleeper_identity import (
    SleeperCatalogRecord,
    SleeperReviewDecision,
    SleeperTeamTransitionReview,
    approve_sleeper_review_decisions,
    approve_sleeper_team_transition_reviews,
    build_approved_sleeper_crosswalk,
    build_sleeper_crosswalk,
    parse_sleeper_catalog,
    propose_sleeper_review_candidates,
    publish_sleeper_crosswalk_dataset,
    require_sleeper_coverage,
    require_sleeper_prepared_pool_coverage,
    write_sleeper_crosswalk_report,
    write_sleeper_review_queue,
)
from nfl_fantasy_assistant.data.sleeper_review import (
    batch_review_candidates,
    load_review_queue_artifact,
    validate_decisions_against_queue,
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


def test_sleeper_catalog_fetcher_uses_documented_local_json_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Response:
        headers = {"etag": "fixture-etag"}

        def __enter__(self) -> Response:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return b'{"fixture":{"player_id":"fixture","position":"QB"}}'

    monkeypatch.setattr(
        "nfl_fantasy_assistant.data.ingestion.urlopen", lambda *_args, **_kwargs: Response()
    )
    ingestor = SnapshotIngestor(tmp_path / "raw", tmp_path / "cache")
    manifest = ingestor.ingest(
        SourceSpec("sleeper", 2026, "players", "Sleeper non-commercial API", ("player_id",)),
        SleeperCatalogFetcher(),
    )
    assert manifest.source_version == "fixture-etag"
    assert manifest.snapshot_file.endswith("snapshot.json")


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
    assert curate_weeks([week_row(1, rushing_yards=-3)], "source-1")[0].rushing_yards == -3
    with pytest.raises(DataValidationError, match="cannot be negative"):
        curate_weeks([week_row(1, rush_attempts=-1)], "source-1")
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


def test_unknown_availability_remains_null_through_feature_construction() -> None:
    rows = [week_row(1, active=None), week_row(2, active=None)]
    features = build_semantic_features(curate_weeks(rows, "source-1"))
    assert features[1].availability_rate_4 is None


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
    with pytest.raises(DataValidationError, match="mutually exclusive"):
        score_stat_line(
            {"field_goals_made": 1, "field_goals_made_50_plus": 1},
            {"field_goals_made": 3, "field_goals_made_50_plus": 5},
        )
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


def test_kicker_and_team_defense_use_explicit_scoring_and_exact_identity() -> None:
    assert (
        score_stat_line(
            {"field_goals_made": 3, "extra_points_made": 2},
            {"field_goals_made": 3, "extra_points_made": 1},
        )
        == 11
    )
    assert (
        score_stat_line(
            {"defensive_sacks": 4, "defensive_interceptions": 2, "points_allowed": 10},
            {"defensive_sacks": 1, "defensive_interceptions": 2, "points_allowed": -0.1},
        )
        == 7
    )
    assert (
        score_stat_line(
            {
                "field_goals_made_0_19": 1,
                "field_goals_made_50_plus": 1,
                "field_goals_missed_30_39": 1,
                "defensive_points_allowed_0": 1,
            },
            {
                "field_goals_made_0_19": 3,
                "field_goals_made_50_plus": 5,
                "field_goals_missed_30_39": -1,
                "defensive_points_allowed_0": 10,
            },
        )
        == 17
    )
    defense = curate_players(
        [
            player_row(
                "def-chi",
                gsis_id=None,
                display_name="Chicago Defense",
                position="DEF",
                nfl_team="CHI",
            )
        ],
        "source-defense",
    )[0]
    pipeline = IdentityPipeline.from_players([defense])
    exact = pipeline.resolve(ExternalReference("nflverse", "def-chi", position="DEF"))
    assert exact.state == "resolved"
    assert (exact.internal_player_id or "").startswith("defense-")
    assert pipeline.mappings()[0].asset_type == "team_defense"
    unresolved = pipeline.resolve(ExternalReference("other", None, "Chicago Defense", "CHI", "DEF"))
    assert unresolved.state == "unresolved"
    context = LeaguePreparationContext(8, ("K", "DEF", "BN"), frozenset({"RB", "WR", "TE"}))
    pool = prepare_baseline_pool(
        [
            (Resolution("resolved", "kicker-1", "fixture", "fixture"), "K", 9.0, "now"),
            (exact, "DEF", 8.0, "now"),
        ],
        "feature-2",
        "dataset-2",
        context,
    )
    assert [item.position for item in pool] == ["K", "DEF"]


def test_sleeper_crosswalk_requires_exact_identifiers_and_team_defense_validity(
    tmp_path: Path,
) -> None:
    players = curate_players(
        [
            player_row(
                "rb-source",
                gsis_id="gsis-rb",
                espn_id="espn-rb",
                position="RB",
                nfl_team="CHI",
            ),
            player_row(
                "k-source",
                gsis_id=None,
                espn_id="espn-k",
                position="K",
                nfl_team="DET",
            ),
            player_row(
                "def-source",
                gsis_id=None,
                espn_id=None,
                display_name="Fixture defense",
                position="DEF",
                nfl_team="CHI",
                valid_from_season=2026,
                valid_through_season=2026,
            ),
            player_row(
                "conflict-source",
                gsis_id="gsis-conflict",
                espn_id="espn-conflict",
                position="WR",
                nfl_team="CHI",
            ),
        ],
        "source-1",
    )
    report = build_sleeper_crosswalk(
        players,
        [
            SleeperCatalogRecord("sleeper-rb", "RB", "CHI", gsis_id="gsis-rb"),
            SleeperCatalogRecord("sleeper-k", "K", "DET", espn_id="espn-k"),
            SleeperCatalogRecord("sleeper-def", "DEF", "CHI"),
            SleeperCatalogRecord("sleeper-missing", "WR", "CHI", gsis_id="unknown"),
            SleeperCatalogRecord(
                "sleeper-incomplete", "RB", "CHI", gsis_id="unknown", espn_id="espn-rb"
            ),
            SleeperCatalogRecord(
                "sleeper-conflict", "RB", "CHI", gsis_id="gsis-rb", espn_id="espn-conflict"
            ),
        ],
        season=2026,
        source_manifest_id="fixture-catalog-v1",
    )
    assert {mapping.external_id for mapping in report.mappings} == {
        "sleeper-rb",
        "sleeper-k",
        "sleeper-def",
    }
    assert report.unresolved_external_ids == ("sleeper-incomplete", "sleeper-missing")
    assert report.conflict_external_ids == ("sleeper-conflict",)
    assert report.coverage_by_position["K"] == (1, 1, 0)
    assert report.coverage_by_position["DEF"] == (1, 1, 0)
    first_checksum = write_sleeper_crosswalk_report(report, tmp_path / "sleeper-crosswalk.json")
    second_checksum = write_sleeper_crosswalk_report(report, tmp_path / "sleeper-crosswalk.json")
    persisted = (tmp_path / "sleeper-crosswalk.json").read_text(encoding="utf-8")
    assert first_checksum == second_checksum
    assert '"source_manifest_id":"fixture-catalog-v1"' in persisted
    assert "display_name" not in persisted
    pipeline = IdentityPipeline(players, mappings=report.mappings)
    assert (
        pipeline.resolve(ExternalReference("sleeper", "sleeper-k", position="K")).state
        == "resolved"
    )
    assert (
        pipeline.resolve(
            ExternalReference("sleeper", "sleeper-def", position="DEF", season=2026)
        ).state
        == "resolved"
    )
    assert (
        pipeline.resolve(
            ExternalReference("sleeper", "sleeper-def", position="DEF", season=2027)
        ).state
        == "unresolved"
    )
    with pytest.raises(DataValidationError, match="required Sleeper"):
        require_sleeper_coverage(report, ("sleeper-rb", "sleeper-missing"))
    prepared = (
        PreparedPlayer(
            report.mappings[0].internal_player_id,
            "RB",
            10.0,
            "2026-08-23T00:00:00+00:00",
            "feature-v1",
            "dataset-v1",
        ),
    )
    covered = require_sleeper_prepared_pool_coverage(
        report,
        prepared,
        prepared_pool_checksum="fixture-prepared-checksum",
        prepared_pool_dataset_version="dataset-v1",
        prepared_pool_feature_version="feature-v1",
    )
    assert covered.prepared_pool_coverage == {"RB": (1, 1, 0)}
    write_sleeper_crosswalk_report(covered, tmp_path / "sleeper-covered-crosswalk.json")
    covered_payload = (tmp_path / "sleeper-covered-crosswalk.json").read_text(encoding="utf-8")
    assert '"prepared_pool_dataset_version":"dataset-v1"' in covered_payload
    assert '"prepared_pool_feature_version":"feature-v1"' in covered_payload
    with pytest.raises(DataValidationError, match="prepared pool"):
        require_sleeper_prepared_pool_coverage(
            report,
            (
                PreparedPlayer(
                    "player-missing",
                    "RB",
                    10.0,
                    "2026-08-23T00:00:00+00:00",
                    "feature-v1",
                    "dataset-v1",
                ),
            ),
            prepared_pool_checksum="fixture-prepared-checksum",
            prepared_pool_dataset_version="dataset-v1",
            prepared_pool_feature_version="feature-v1",
        )


def test_season_team_defense_assets_are_identity_only_and_season_valid() -> None:
    defenses = build_season_team_defense_assets(
        ("CHI", "DET"),
        season=2026,
        source_manifest_id="sleeper-catalog-v1",
        source_updated_at="2026-08-23T00:00:00+00:00",
    )
    assert [asset.source_player_id for asset in defenses] == ["defense:CHI", "defense:DET"]
    assert all(asset.asset_type == "team_defense" for asset in defenses)
    report = build_sleeper_crosswalk(
        defenses,
        [SleeperCatalogRecord("sleeper-def", "DEF", "CHI")],
        season=2026,
        source_manifest_id="sleeper-catalog-v1",
    )
    assert report.mappings[0].asset_type == "team_defense"
    assert report.mappings[0].external_id == "sleeper-def"


def test_sleeper_crosswalk_is_published_in_a_new_immutable_dataset_version(
    tmp_path: Path,
) -> None:
    players = curate_players([player_row()], "nflverse-source-1")
    report = build_sleeper_crosswalk(
        players,
        [SleeperCatalogRecord("sleeper-rb", "RB", "CHI", gsis_id="00-003")],
        season=2026,
        source_manifest_id="sleeper-catalog-1",
    )
    prepared = (
        PreparedPlayer(
            report.mappings[0].internal_player_id,
            "RB",
            10.0,
            "2026-08-23T00:00:00+00:00",
            "feature-v1",
            "prepared-v1",
        ),
    )
    prepared_path = tmp_path / "prepared.parquet"
    prepared_checksum = write_prepared_parquet(prepared, prepared_path)
    recommendation_path = tmp_path / "recommendation-inputs.parquet"
    recommendation_checksum = write_prepared_recommendation_inputs_parquet(
        (
            PreparedRecommendationInput(
                prepared[0].internal_player_id,
                "RB",
                15.0,
                10.0,
                20.0,
                0.8,
                (),
                "projection-v3",
                "semantic-v3",
                0.7,
                0.8,
                0.1,
                0.7,
                (),
                "value-v1",
                "value-minmax-v1",
                "2026-08-23T00:00:00+00:00",
                "feature-v1",
                "prepared-v1",
            ),
        ),
        recommendation_path,
    )
    parent_manifest = dataset_manifest(
        "prepared-v1",
        "feature-v1",
        "prepared-v1",
        ("nflverse-source-1",),
        {"prepared": "v2", "prepared_recommendation_inputs": "v1"},
        (
            OutputFile("prepared.parquet", prepared_checksum, 1),
            OutputFile("prepared_recommendation_inputs.parquet", recommendation_checksum, 1),
        ),
        {name: True for name in DatasetPublisher.REQUIRED_CHECKS},
        ("CC BY 4.0",),
    )
    root = tmp_path / "published"
    parent_version = DatasetPublisher(root).publish(
        parent_manifest,
        {
            "prepared.parquet": prepared_path.read_bytes(),
            "prepared_recommendation_inputs.parquet": recommendation_path.read_bytes(),
        },
        {"prepared.parquet": 1, "prepared_recommendation_inputs.parquet": 1},
    )
    covered = require_sleeper_prepared_pool_coverage(
        report,
        prepared,
        prepared_pool_checksum=prepared_checksum,
        prepared_pool_dataset_version="prepared-v1",
        prepared_pool_feature_version="feature-v1",
    )

    publication = publish_sleeper_crosswalk_dataset(
        covered,
        parent_version,
        root,
        dataset_version="prepared-with-sleeper-v1",
        players=players,
    )

    assert publication.version == root / "versions" / "prepared-with-sleeper-v1"
    assert publication.report.prepared_pool_dataset_version == "prepared-with-sleeper-v1"
    assert (publication.version / "asset_external_ids.parquet").is_file()
    assert (publication.version / "sleeper_observed_identities.parquet").is_file()
    assert (publication.version / "sleeper_crosswalk_coverage.parquet").is_file()
    published_pool = read_published_prepared_pool(publication.version)
    assert published_pool.dataset_version == "prepared-with-sleeper-v1"
    assert published_pool.players[0].dataset_version == "prepared-with-sleeper-v1"
    assert (
        read_prepared_recommendation_inputs_parquet(
            publication.version / "prepared_recommendation_inputs.parquet"
        )[0].dataset_version
        == "prepared-with-sleeper-v1"
    )


def test_sleeper_catalog_parser_retains_only_mapping_fields() -> None:
    records = parse_sleeper_catalog(
        b'{"sleeper-k":{"player_id":"sleeper-k","position":"K","team":"DET","gsis_id":null,"espn_id":"espn-k","full_name":"not-retained"}}'
    )
    assert records == (
        SleeperCatalogRecord(
            "sleeper-k", "K", "DET", display_name="not-retained", espn_id="espn-k"
        ),
    )
    with pytest.raises(DataValidationError, match="key conflicts"):
        parse_sleeper_catalog(b'{"one":{"player_id":"two","position":"QB"}}')


def test_sleeper_review_candidates_require_explicit_approval(tmp_path: Path) -> None:
    player = curate_players(
        [player_row("reviewed", gsis_id=None, espn_id=None, display_name="Fixture Player")],
        "source-1",
    )[0]
    record = SleeperCatalogRecord("sleeper-reviewed", "RB", "CHI", display_name="Fixture Player")
    candidate = propose_sleeper_review_candidates([player], [record])
    assert len(candidate) == 1
    assert candidate[0].batch_eligible
    assert batch_review_candidates(candidate, ()) == candidate
    assert (
        batch_review_candidates(
            candidate,
            [
                SleeperReviewDecision(
                    "sleeper-reviewed",
                    candidate[0].candidate_internal_player_id,
                    "operator",
                    "2026-08-22T00:00:00+00:00",
                    "Already handled",
                )
            ],
        )
        == ()
    )
    approved = approve_sleeper_review_decisions(
        [player],
        [record],
        [
            SleeperReviewDecision(
                "sleeper-reviewed",
                candidate[0].candidate_internal_player_id,
                "operator",
                "2026-08-22T00:00:00+00:00",
                "Reviewed candidate evidence",
            )
        ],
        season=2026,
        source_manifest_id="fixture-catalog-v1",
    )
    assert approved[0].method == "sleeper_reviewed_override_v1"
    queue_checksum = write_sleeper_review_queue(
        candidate, tmp_path / "review-queue.json", source_manifest_id="fixture-catalog-v1"
    )
    assert queue_checksum
    assert "requires_explicit_review" in (tmp_path / "review-queue.json").read_text()
    queue = load_review_queue_artifact(tmp_path / "review-queue.json")
    decisions = validate_decisions_against_queue(
        queue,
        [
            SleeperReviewDecision(
                "sleeper-reviewed",
                candidate[0].candidate_internal_player_id,
                "operator",
                "2026-08-22T00:00:00+00:00",
                "Reviewed candidate evidence",
            )
        ],
    )
    report = build_approved_sleeper_crosswalk(
        [player],
        [record],
        decisions,
        season=2026,
        source_manifest_id="fixture-catalog-v1",
        review_queue_checksum=queue.checksum,
        review_decisions_checksum="fixture-decisions-checksum",
        player_assets_checksum="fixture-player-assets-checksum",
    )
    assert report.unresolved_external_ids == ()
    assert report.mappings[0].method == "sleeper_reviewed_override_v1"
    assert report.review_queue_checksum == queue.checksum
    with pytest.raises(DataValidationError, match="position or NFL team"):
        approve_sleeper_review_decisions(
            [player],
            [SleeperCatalogRecord("sleeper-wrong", "WR", "CHI", display_name="Fixture Player")],
            [
                SleeperReviewDecision(
                    "sleeper-wrong",
                    candidate[0].candidate_internal_player_id,
                    "operator",
                    "2026-08-22T00:00:00+00:00",
                    "Must fail",
                )
            ],
            season=2026,
            source_manifest_id="fixture-catalog-v1",
        )


def test_sleeper_team_transition_requires_explicit_observed_teams() -> None:
    player = curate_players(
        [player_row("transition", gsis_id=None, espn_id=None, position="RB", nfl_team="CHI")],
        "source-1",
    )[0]
    transition = SleeperTeamTransitionReview(
        "sleeper-transition",
        internal_player_id(player),
        "CHI",
        "DET",
        "operator",
        "2026-08-23T00:00:00+00:00",
        "Reviewer verified the current team transition.",
    )
    mappings = approve_sleeper_team_transition_reviews(
        [player],
        [SleeperCatalogRecord("sleeper-transition", "RB", "DET")],
        [transition],
        season=2026,
        source_manifest_id="fixture-catalog-v1",
    )
    assert mappings[0].method == "sleeper_reviewed_team_transition_v1"
    with pytest.raises(DataValidationError, match="observed team change"):
        approve_sleeper_team_transition_reviews(
            [player],
            [SleeperCatalogRecord("sleeper-transition", "RB", "DET")],
            [
                SleeperTeamTransitionReview(
                    "sleeper-transition",
                    internal_player_id(player),
                    "CHI",
                    "CHI",
                    "operator",
                    "2026-08-23T00:00:00+00:00",
                    "Must fail.",
                )
            ],
            season=2026,
            source_manifest_id="fixture-catalog-v1",
        )


def test_kicker_and_team_defense_features_are_time_safe_and_position_specific() -> None:
    kicker_features = build_semantic_features(
        curate_weeks(
            [
                week_row(
                    1,
                    player_id="kicker-1",
                    position="K",
                    field_goal_attempts=3,
                    field_goals_made=2,
                    field_goals_made_50_plus=1,
                    field_goals_missed_30_39=1,
                    extra_point_attempts=2,
                    extra_points_made=2,
                    extra_points_missed=1,
                ),
                week_row(
                    2,
                    player_id="kicker-1",
                    position="K",
                    field_goal_attempts=4,
                    field_goals_made=4,
                    field_goals_made_50_plus=2,
                    field_goals_missed_30_39=0,
                    extra_point_attempts=3,
                    extra_points_made=3,
                    extra_points_missed=0,
                ),
            ],
            "source-k",
        )
    )
    assert kicker_features[0].kicking_attempts_per_game_4 is None
    assert kicker_features[1].kicking_attempts_per_game_4 == 3
    assert kicker_features[1].kicking_conversion_rate_4 == pytest.approx(2 / 3)
    assert kicker_features[1].field_goals_made_50_plus_per_game_4 == 1
    assert kicker_features[1].field_goals_missed_30_39_per_game_4 == 1
    assert kicker_features[1].extra_points_missed_per_game_4 == 1
    assert kicker_features[1].field_goals_made_0_19_per_game_4 is None
    defense_features = build_semantic_features(
        curate_weeks(
            [
                week_row(
                    1,
                    player_id="def-chi",
                    position="DEF",
                    defensive_sacks=3,
                    defensive_interceptions=1,
                    defensive_fumble_recoveries=1,
                    points_allowed=17,
                ),
                week_row(
                    2,
                    player_id="def-chi",
                    position="DEF",
                    defensive_sacks=2,
                    defensive_interceptions=2,
                    defensive_fumble_recoveries=0,
                    points_allowed=21,
                ),
            ],
            "source-def",
        )
    )
    assert defense_features[1].defensive_sacks_per_game_4 == 3
    assert defense_features[1].turnovers_forced_per_game_4 == 2
    assert defense_features[1].points_allowed_per_game_4 == 17


def test_pbp_transform_publishes_exact_kicker_and_team_defense_assets(tmp_path: Path) -> None:
    base = {
        "game_id": "2025_01_CHI_DET",
        "home_team": "CHI",
        "away_team": "DET",
        "season": 2025,
        "week": 1,
        "total_home_score": 0,
        "total_away_score": 0,
        "field_goal_attempt": 0,
        "extra_point_attempt": 0,
        "sack": 0,
        "interception": 0,
        "fumble_lost": 0,
        "return_touchdown": 0,
    }
    transformed = transform_pbp_k_def(
        (
            {
                **base,
                "posteam": "DET",
                "defteam": "CHI",
                "play_type": "pass",
                "yards_gained": 7,
                "sack": 1,
                "interception": 1,
            },
            {
                **base,
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "field_goal",
                "kicker_player_id": "00-kicker",
                "kicker_player_name": "Kicker One",
                "field_goal_attempt": 1,
                "field_goal_result": "made",
                "kick_distance": 51,
                "total_home_score": 3,
            },
            {
                **base,
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "field_goal",
                "kicker_player_id": "00-kicker",
                "kicker_player_name": "Kicker One",
                "field_goal_attempt": 1,
                "field_goal_result": "missed",
                "kick_distance": 32,
                "total_home_score": 3,
            },
            {
                **base,
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "field_goal",
                "kicker_player_id": "00-kicker",
                "kicker_player_name": "Kicker One",
                "field_goal_attempt": 1,
                "field_goal_result": "blocked",
                "kick_distance": 42,
                "total_home_score": 3,
            },
            {
                **base,
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "extra_point",
                "kicker_player_id": "00-kicker",
                "kicker_player_name": "Kicker One",
                "extra_point_attempt": 1,
                "extra_point_result": "good",
                "total_home_score": 10,
            },
            {
                **base,
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "extra_point",
                "kicker_player_id": "00-kicker",
                "kicker_player_name": "Kicker One",
                "extra_point_attempt": 1,
                "extra_point_result": "failed",
                "total_home_score": 10,
            },
            {
                **base,
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "extra_point",
                "kicker_player_id": "00-kicker",
                "kicker_player_name": "Kicker One",
                "extra_point_attempt": 1,
                "extra_point_result": "blocked",
                "total_home_score": 10,
            },
            {
                **base,
                "posteam": "DET",
                "defteam": "CHI",
                "play_type": "pass",
                "yards_gained": 0,
                "return_touchdown": 1,
                "td_team": "CHI",
                "safety": 1,
                "total_home_score": 17,
            },
            {
                **base,
                "season_type": "POST",
                "posteam": "CHI",
                "defteam": "DET",
                "play_type": "field_goal",
                "kicker_player_id": "00-postseason",
                "kicker_player_name": "Postseason Kicker",
                "field_goal_attempt": 1,
                "field_goal_result": "made",
            },
        ),
        source_updated_at="2026-08-22T00:00:00+00:00",
    )
    players = curate_players(transformed.players, "pbp-source-1")
    weeks = curate_weeks(transformed.weeks, "pbp-source-1")
    validate_curated_tables(players, weeks, {"K": 1, "DEF": 2})
    chicago = next(row for row in weeks if row.source_player_id == "defense:CHI")
    assert chicago.defensive_sacks == 1
    assert chicago.defensive_interceptions == 1
    assert chicago.defensive_touchdowns == 1
    assert chicago.defensive_safeties == 1
    assert chicago.defensive_points_allowed_0 == 1
    assert chicago.points_allowed == 0
    assert chicago.yards_allowed == 7
    kicker = next(row for row in weeks if row.source_player_id == "00-kicker")
    assert kicker.field_goal_attempts == 3
    assert kicker.field_goals_missed == 2
    assert kicker.field_goals_made_50_plus == 1
    assert kicker.field_goals_missed_30_39 == 1
    assert kicker.field_goals_missed_40_49 == 1
    assert kicker.field_goals_made_0_19 == 0
    assert kicker.field_goals_missed_50_plus == 0
    assert kicker.extra_points_made == 1
    assert kicker.extra_points_missed == 2
    with pytest.raises(DataValidationError, match="extra-point result"):
        transform_pbp_k_def(
            (
                {
                    **base,
                    "posteam": "CHI",
                    "defteam": "DET",
                    "play_type": "extra_point",
                    "kicker_player_id": "00-kicker",
                    "kicker_player_name": "Kicker One",
                    "extra_point_attempt": 1,
                    "extra_point_result": "unknown",
                },
            ),
            source_updated_at="2026-08-22T00:00:00+00:00",
        )
    assert all(row.source_player_id != "00-postseason" for row in players)
    pipeline = IdentityPipeline.from_players(players)
    assert (
        pipeline.resolve(ExternalReference("nflverse", "defense:CHI", position="DEF")).state
        == "resolved"
    )
    defense_id = pipeline.resolve(
        ExternalReference("nflverse", "defense:CHI", position="DEF")
    ).internal_player_id
    assert defense_id is not None
    provider_pipeline = IdentityPipeline(
        players,
        mappings=(
            IdentityMapping(
                "sleeper",
                "fixture-team-defense-chi",
                defense_id,
                "provider_exact_v2",
                "sanitized fixture",
                asset_type="team_defense",
            ),
        ),
    )
    assert (
        provider_pipeline.resolve(
            ExternalReference("sleeper", "fixture-team-defense-chi", position="DEF")
        ).state
        == "resolved"
    )
    assert (
        provider_pipeline.resolve(
            ExternalReference("sleeper", "fixture-team-defense-chi", position="DEF", season=2026)
        ).state
        == "unresolved"
    )
    assert (
        provider_pipeline.resolve(
            ExternalReference("sleeper", "fixture-team-defense-chi", position="RB")
        ).state
        == "conflict"
    )
    assert (
        pipeline.resolve(ExternalReference("nflverse", "00-kicker", position="K")).state
        == "resolved"
    )
    kicker_id = pipeline.resolve(
        ExternalReference("nflverse", "00-kicker", position="K")
    ).internal_player_id
    assert kicker_id is not None
    prepared = prepare_baseline_pool(
        (
            (Resolution("resolved", kicker_id, "exact", "fixture"), "K", 11.0, "source-now"),
            (Resolution("resolved", defense_id, "exact", "fixture"), "DEF", 9.0, "source-now"),
        ),
        "feature-v2",
        "k-def-fixture-v1",
        LeaguePreparationContext(8, ("K", "DEF", "BN"), frozenset({"RB", "WR", "TE"})),
    )

    player_path = tmp_path / "players.parquet"
    week_path = tmp_path / "weeks.parquet"
    prepared_path = tmp_path / "prepared.parquet"
    write_curated_parquet(players, PLAYER_SCHEMA, player_path)
    write_curated_parquet(weeks, WEEK_SCHEMA, week_path)
    write_prepared_parquet(prepared, prepared_path)
    assert read_prepared_parquet(prepared_path) == tuple(prepared)
    files = {
        "players.parquet": player_path.read_bytes(),
        "weeks.parquet": week_path.read_bytes(),
        "prepared.parquet": prepared_path.read_bytes(),
    }
    row_counts = {
        "players.parquet": len(players),
        "weeks.parquet": len(weeks),
        "prepared.parquet": len(prepared),
    }
    outputs = tuple(
        OutputFile(
            name,
            hashlib.sha256(payload).hexdigest(),
            row_counts[name],
        )
        for name, payload in sorted(files.items())
    )
    manifest = dataset_manifest(
        "k-def-fixture-v1",
        "feature-v2",
        "k-def-pbp-v1",
        ("pbp-source-1",),
        {"players": "v2", "player_week_features": "v2", "prepared": "v2"},
        outputs,
        {name: True for name in DatasetPublisher.REQUIRED_CHECKS},
        ("CC BY 4.0",),
    )
    publisher = DatasetPublisher(tmp_path / "published")
    version = publisher.publish(manifest, files, row_counts)
    assert publisher.active_version() == ("k-def-fixture-v1", "feature-v2")
    published_pool = read_published_prepared_pool(version)
    assert published_pool.players == tuple(prepared)
    assert published_pool.dataset_version == "k-def-fixture-v1"
    assert published_pool.feature_version == "feature-v2"


@pytest.mark.parametrize(
    ("distance", "result", "expected_field"),
    (
        (0, "made", "field_goals_made_0_19"),
        (19, "missed", "field_goals_missed_0_19"),
        (20, "made", "field_goals_made_20_29"),
        (29, "missed", "field_goals_missed_20_29"),
        (30, "made", "field_goals_made_30_39"),
        (39, "missed", "field_goals_missed_30_39"),
        (40, "made", "field_goals_made_40_49"),
        (49, "missed", "field_goals_missed_40_49"),
        (50, "made", "field_goals_made_50_plus"),
        (63, "missed", "field_goals_missed_50_plus"),
    ),
)
def test_pbp_kicker_transform_preserves_each_field_goal_band(
    distance: int, result: str, expected_field: str
) -> None:
    transformed = transform_pbp_k_def(
        (
            {
                "game_id": "fixture-game",
                "home_team": "CHI",
                "away_team": "DET",
                "season": 2025,
                "week": 1,
                "total_home_score": 0,
                "total_away_score": 0,
                "posteam": "CHI",
                "play_type": "field_goal",
                "field_goal_attempt": 1,
                "field_goal_result": result,
                "kick_distance": distance,
                "kicker_player_id": "fixture-kicker",
                "kicker_player_name": "Fixture Kicker",
            },
        ),
        source_updated_at="2026-08-23T00:00:00+00:00",
    )
    week = transformed.weeks[0]
    assert week[expected_field] == 1
    assert week["field_goal_attempts"] == 1


@pytest.mark.parametrize(
    ("points_allowed", "expected_field"),
    (
        (0, "defensive_points_allowed_0"),
        (1, "defensive_points_allowed_1_6"),
        (6, "defensive_points_allowed_1_6"),
        (7, "defensive_points_allowed_7_13"),
        (13, "defensive_points_allowed_7_13"),
        (14, "defensive_points_allowed_14_20"),
        (20, "defensive_points_allowed_14_20"),
        (21, "defensive_points_allowed_21_27"),
        (27, "defensive_points_allowed_21_27"),
        (28, "defensive_points_allowed_28_34"),
        (34, "defensive_points_allowed_28_34"),
        (35, "defensive_points_allowed_35_plus"),
        (52, "defensive_points_allowed_35_plus"),
    ),
)
def test_pbp_defense_transform_preserves_each_points_allowed_band(
    points_allowed: int, expected_field: str
) -> None:
    transformed = transform_pbp_k_def(
        (
            {
                "game_id": "fixture-game",
                "home_team": "CHI",
                "away_team": "DET",
                "season": 2025,
                "week": 1,
                "total_home_score": 0,
                "total_away_score": points_allowed,
                "posteam": "DET",
                "defteam": "CHI",
                "play_type": "pass",
                "yards_gained": 0,
            },
        ),
        source_updated_at="2026-08-23T00:00:00+00:00",
    )
    week = transformed.weeks[0]
    assert week[expected_field] == 1
    assert week["points_allowed"] == points_allowed


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
