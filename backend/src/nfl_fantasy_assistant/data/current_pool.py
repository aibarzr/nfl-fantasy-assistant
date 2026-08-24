"""Local construction of a current, scoring-aware Sleeper prepared pool.

This is deliberately an offline data adapter.  It consumes already-verified local snapshots and a
locally supplied neutral league configuration; it never calls Sleeper or exposes source-shaped
records to the draft runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from nfl_fantasy_assistant.models.projection import (
    ProjectionError,
    ProjectionFeatures,
    ProjectionInput,
    project_player,
)
from nfl_fantasy_assistant.models.valuation import ValueInput, value_players

from .curation import CuratedPlayer, CuratedWeek, curate_weeks, read_curated_players_parquet
from .durability import (
    DurabilityFeature,
    ParticipationState,
    PlayerWeekParticipation,
    build_durability_features,
)
from .errors import DataValidationError
from .features import FEATURE_VERSION, SemanticFeature, build_semantic_features
from .identity import Resolution, internal_player_id
from .k_def import transform_pbp_k_def
from .preparation import (
    LeaguePreparationContext,
    PreparedPlayer,
    PreparedRecommendationInput,
    prepare_baseline_pool,
    write_prepared_parquet,
    write_prepared_recommendation_inputs_parquet,
)
from .publishing import DatasetPublisher, OutputFile, dataset_manifest


@dataclass(frozen=True, slots=True)
class VerifiedSnapshot:
    manifest_id: str
    dataset: str
    season: int
    retrieved_at: str
    license_note: str
    rows: tuple[Mapping[str, object], ...]


@dataclass(frozen=True, slots=True)
class LocalLeagueConfiguration:
    team_count: int
    roster_slots: tuple[str, ...]
    flex_eligible_positions: frozenset[str]
    scoring_rules: Mapping[str, float]

    @property
    def preparation_context(self) -> LeaguePreparationContext:
        return LeaguePreparationContext(
            self.team_count, self.roster_slots, self.flex_eligible_positions
        )


@dataclass(frozen=True, slots=True)
class CurrentPoolBuild:
    prepared: tuple[PreparedPlayer, ...]
    recommendation_inputs: tuple[PreparedRecommendationInput, ...]
    source_manifest_ids: tuple[str, ...]
    license_notes: tuple[str, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_verified_snapshot(manifest_path: Path, snapshot_path: Path) -> VerifiedSnapshot:
    """Read a local raw snapshot only after proving it matches its manifest checksum."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DataValidationError("source manifest is unreadable") from error
    required = (
        "manifest_id",
        "dataset",
        "season",
        "checksum_sha256",
        "retrieved_at",
        "license_note",
    )
    if any(not manifest.get(field) for field in required):
        raise DataValidationError("source manifest is incomplete")
    if _sha256(snapshot_path) != manifest["checksum_sha256"]:
        raise DataValidationError("source snapshot checksum does not match its manifest")
    try:
        rows = tuple(pq.read_table(snapshot_path).to_pylist())
    except (OSError, ValueError) as error:
        raise DataValidationError("source snapshot is not readable Parquet") from error
    if not rows:
        raise DataValidationError("source snapshot has no rows")
    return VerifiedSnapshot(
        manifest_id=str(manifest["manifest_id"]),
        dataset=str(manifest["dataset"]),
        season=int(manifest["season"]),
        retrieved_at=str(manifest["retrieved_at"]),
        license_note=str(manifest["license_note"]),
        rows=rows,
    )


def read_local_league_configuration(path: Path) -> LocalLeagueConfiguration:
    """Load a neutral, local-only configuration emitted from the validated adapter boundary."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DataValidationError("league configuration is unreadable") from error
    if not isinstance(value, dict) or value.get("team_count") != 8:
        raise DataValidationError("prepared pool requires the supported eight-team league")
    raw_slots = value.get("roster_slots")
    raw_rules = value.get("scoring_rules")
    if not isinstance(raw_slots, list) or not isinstance(raw_rules, dict):
        raise DataValidationError("league configuration requires roster slots and scoring rules")
    slots: list[str] = []
    flex: set[str] = set()
    for item in raw_slots:
        if not isinstance(item, dict) or not isinstance(item.get("eligible_positions"), list):
            raise DataValidationError("league roster slot is invalid")
        eligible = frozenset(str(position) for position in item["eligible_positions"])
        if item.get("is_bench") is not True:
            slots.extend(sorted(eligible) if len(eligible) > 1 else eligible)
        if len(eligible) > 1:
            flex.update(eligible)
    rules: dict[str, float] = {}
    for name, raw_value in raw_rules.items():
        if not isinstance(name, str) or not isinstance(raw_value, int | float):
            raise DataValidationError("league scoring rule is invalid")
        value_as_float = float(raw_value)
        if not math.isfinite(value_as_float):
            raise DataValidationError("league scoring rule must be finite")
        rules[name] = value_as_float
    from .preparation import validate_prepared_scoring_rules

    validate_prepared_scoring_rules(rules)
    return LocalLeagueConfiguration(8, tuple(slots), frozenset(flex), rules)


def read_crosswalk_internal_ids(
    report_path: Path, assets_path: Path, *, season: int
) -> frozenset[str]:
    """Use only a checksum-pinned local crosswalk as candidate identity evidence."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DataValidationError("Sleeper crosswalk report is unreadable") from error
    if report.get("provider") != "sleeper" or report.get("season") != season:
        raise DataValidationError("Sleeper crosswalk report has a different provider or season")
    expected_assets = report.get("input_checksums", {}).get("player_assets")
    if not isinstance(expected_assets, str) or expected_assets != _sha256(assets_path):
        raise DataValidationError("Sleeper crosswalk report does not pin the supplied asset table")
    mappings = report.get("mappings")
    if not isinstance(mappings, list):
        raise DataValidationError("Sleeper crosswalk report has no mappings")
    ids = [mapping.get("internal_player_id") for mapping in mappings if isinstance(mapping, dict)]
    if not ids or any(not isinstance(identifier, str) or not identifier for identifier in ids):
        raise DataValidationError("Sleeper crosswalk report has an invalid mapping")
    return frozenset(identifier for identifier in ids if isinstance(identifier, str))


def _number(row: Mapping[str, object], name: str) -> float | None:
    value = row.get(name)
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        raise DataValidationError(f"nflverse player-stat field {name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise DataValidationError(f"nflverse player-stat field {name} must be numeric") from error


def _historical_skill_rows(snapshot: VerifiedSnapshot) -> list[Mapping[str, object]]:
    if snapshot.dataset != "player_stats" or snapshot.season not in range(2022, 2026):
        raise DataValidationError(
            "historical player-stat snapshot is outside the approved coverage"
        )
    fields = {
        "rush_attempts": "carries",
        "targets": "targets",
        "receptions": "receptions",
        "passing_attempts": "attempts",
        "air_yards": "receiving_air_yards",
        "receiving_yards": "receiving_yards",
        "rushing_yards": "rushing_yards",
        "passing_yards": "passing_yards",
    }
    result: list[Mapping[str, object]] = []
    for row in snapshot.rows:
        position = str(row.get("position") or "").upper()
        if row.get("season_type") != "REG" or position not in {"QB", "RB", "WR", "TE"}:
            continue
        player_id = row.get("player_id")
        week = row.get("week")
        if not isinstance(player_id, str) or not player_id or week is None:
            raise DataValidationError("player-stat row lacks player identity or week")
        touchdowns = sum(
            _number(row, field) or 0.0 for field in ("passing_tds", "rushing_tds", "receiving_tds")
        )
        result.append(
            {
                "player_id": player_id,
                "season": snapshot.season,
                "week": week,
                "position": position,
                **{target: _number(row, source) for target, source in fields.items()},
                "touchdowns": touchdowns,
                # Player statistics establish production only. They do not establish that a
                # player was healthy or available for a team game.
                "active": None,
                "source_updated_at": snapshot.retrieved_at,
            }
        )
    if not result:
        raise DataValidationError(
            "historical player-stat snapshot has no regular-season skill rows"
        )
    return result


def build_historical_weeks(
    player_stat_snapshots: Sequence[VerifiedSnapshot], pbp_snapshots: Sequence[VerifiedSnapshot]
) -> tuple[CuratedWeek, ...]:
    """Combine approved skill-position and exact PBP K/DEF histories at the curated boundary."""
    if {snapshot.season for snapshot in player_stat_snapshots} != set(range(2022, 2026)):
        raise DataValidationError("one 2022–2025 player-stat snapshot is required per season")
    if {snapshot.season for snapshot in pbp_snapshots} != set(range(2022, 2026)):
        raise DataValidationError("one 2022–2025 PBP snapshot is required per season")
    pbp_rows: list[Mapping[str, object]] = []
    kicker_ids: set[str] = set()
    for snapshot in pbp_snapshots:
        if snapshot.dataset != "pbp":
            raise DataValidationError("K/DEF history requires nflverse PBP snapshots")
        transformed = transform_pbp_k_def(snapshot.rows, source_updated_at=snapshot.retrieved_at)
        pbp_rows.extend(transformed.weeks)
        kicker_ids.update(
            str(row["player_id"]) for row in transformed.weeks if row["position"] == "K"
        )
    # PBP owns K identity and scoring bands. A rare special-teams appearance can otherwise give a
    # kicker a second non-K player-stat row for the same source player/week.
    rows = [
        row
        for snapshot in player_stat_snapshots
        for row in _historical_skill_rows(snapshot)
        if str(row["player_id"]) not in kicker_ids
    ]
    rows.extend(pbp_rows)
    return tuple(curate_weeks(rows, "multiple-source-manifests"))


def build_historical_durability(snapshot: VerifiedSnapshot) -> tuple[DurabilityFeature, ...]:
    """Validate an exact derived eligibility calendar before it can supply durability features."""
    if snapshot.dataset != "participation_calendar":
        raise DataValidationError("durability requires a participation_calendar snapshot")
    observations: list[PlayerWeekParticipation] = []
    for row in snapshot.rows:
        try:
            state = ParticipationState(str(row["state"]))
            player_id = str(row["player_id"])
            nfl_team = str(row["nfl_team"])
            season_raw = row["season"]
            week_raw = row["week"]
            if not isinstance(season_raw, int | str) or not isinstance(week_raw, int | str):
                raise ValueError("season/week must be integer-like")
            season = int(season_raw)
            week = int(week_raw)
        except (KeyError, TypeError, ValueError) as error:
            raise DataValidationError(
                "participation calendar row has invalid exact fields"
            ) from error
        observations.append(
            PlayerWeekParticipation(
                player_id,
                nfl_team,
                season,
                week,
                state,
                (snapshot.manifest_id,),
            )
        )
    if not observations:
        raise DataValidationError("participation calendar has no observations")
    return build_durability_features(observations)


def _current_roster_ids(snapshot: VerifiedSnapshot) -> frozenset[str]:
    if snapshot.dataset != "rosters" or snapshot.season != 2026:
        raise DataValidationError("current candidate eligibility requires the 2026 roster snapshot")
    ids = {
        str(row["gsis_id"])
        for row in snapshot.rows
        if str(row.get("position") or "").upper() in {"QB", "RB", "WR", "TE", "K"}
        and row.get("gsis_id")
    }
    if not ids:
        raise DataValidationError("current roster snapshot has no supported player identities")
    return frozenset(ids)


def _feature_input(feature: SemanticFeature, source_updated_at: str) -> ProjectionFeatures:
    try:
        timestamp = datetime.fromisoformat(source_updated_at).astimezone(UTC)
    except ValueError as error:
        raise DataValidationError(
            "candidate source timestamp must be ISO-8601 with a timezone"
        ) from error
    values = {
        field.removesuffix("_4"): getattr(feature, field)
        for field in SemanticFeature.__dataclass_fields__
        if field.endswith("_4")
    }
    values["historical_points_per_game"] = feature.historical_production_points_per_game
    values["durability_rate"] = feature.durability_rate_4
    values["source_updated_at"] = timestamp
    return ProjectionFeatures(**values)


def build_current_pool(
    players: Iterable[CuratedPlayer],
    weeks: Iterable[CuratedWeek],
    current_roster_snapshot: VerifiedSnapshot,
    crosswalk_internal_ids: frozenset[str],
    league: LocalLeagueConfiguration,
    *,
    dataset_version: str,
    target_size: int = 300,
    durability_features: Sequence[DurabilityFeature] = (),
    durability_source_manifest_ids: Sequence[str] = (),
    durability_license_notes: Sequence[str] = (),
) -> CurrentPoolBuild:
    """Build the prepared pool and its exact offline recommendation inputs together."""
    roster_ids = _current_roster_ids(current_roster_snapshot)
    assets = tuple(players)
    by_source = {player.source_player_id: player for player in assets}
    if len(by_source) != len(assets):
        raise DataValidationError("current asset table has duplicate source IDs")
    features = build_semantic_features(weeks, durability_features)
    latest: dict[str, SemanticFeature] = {}
    for feature in features:
        if (previous := latest.get(feature.source_player_id)) is None or (
            feature.season,
            feature.week,
        ) > (previous.season, previous.week):
            latest[feature.source_player_id] = feature

    candidates: list[tuple[CuratedPlayer, SemanticFeature]] = []
    for player in assets:
        current = player.source_player_id in roster_ids or (
            player.position == "DEF"
            and player.valid_from_season is not None
            and player.valid_from_season <= 2026
            and (player.valid_through_season is None or 2026 <= player.valid_through_season)
        )
        if not current or internal_player_id(player) not in crosswalk_internal_ids:
            continue
        candidate_feature = latest.get(player.source_player_id)
        if candidate_feature is not None:
            candidates.append((player, candidate_feature))
    if not candidates:
        raise DataValidationError("no current crosswalk-resolved assets have historical evidence")

    now = datetime.fromisoformat(current_roster_snapshot.retrieved_at).astimezone(UTC)
    projections = []
    projection_sources: dict[str, CuratedPlayer] = {}
    for player, feature in candidates:
        try:
            projection = project_player(
                ProjectionInput(
                    internal_player_id(player),
                    player.position,
                    _feature_input(feature, player.source_updated_at),
                ),
                league.scoring_rules,
                now=now,
            )
        except ProjectionError as error:
            if player.position in {"K", "DEF"}:
                raise DataValidationError(
                    f"{player.position} candidate lacks required exact scoring evidence"
                ) from error
            continue
        projections.append(projection)
        projection_sources[projection.internal_player_id] = player
    values = value_players((ValueInput(projection) for projection in projections), now=now)
    prepared = prepare_baseline_pool(
        (
            (
                Resolution(
                    "resolved", value.internal_player_id, "sleeper_crosswalk", "local report"
                ),
                value.position,
                value.value_score,
                projection_sources[value.internal_player_id].source_updated_at,
            )
            for value in values
        ),
        FEATURE_VERSION,
        dataset_version,
        league.preparation_context,
        target_size,
    )
    if not prepared:
        raise DataValidationError("current prepared pool is empty")
    if any(player.internal_player_id not in crosswalk_internal_ids for player in prepared):
        raise DataValidationError("prepared pool contains a Sleeper-unmapped asset")
    by_projection = {projection.internal_player_id: projection for projection in projections}
    by_value = {value.internal_player_id: value for value in values}
    feature_by_internal = {internal_player_id(player): feature for player, feature in candidates}
    recommendation_inputs: list[PreparedRecommendationInput] = []
    for prepared_player in prepared:
        input_projection = by_projection.get(prepared_player.internal_player_id)
        input_value = by_value.get(prepared_player.internal_player_id)
        if (
            input_projection is None
            or input_value is None
            or input_projection.position != prepared_player.position
        ):
            raise DataValidationError("prepared player lacks matching projection and value output")
        current_feature = feature_by_internal.get(prepared_player.internal_player_id)
        if current_feature is None:
            raise DataValidationError("prepared player lacks matching historical feature")
        market_prior = input_value.components.get("market_prior")
        if not isinstance(market_prior, float):
            raise DataValidationError("prepared value lacks the runtime market prior")
        recommendation_inputs.append(
            PreparedRecommendationInput(
                internal_player_id=prepared_player.internal_player_id,
                position=prepared_player.position,
                expected_points=input_projection.expected_points,
                floor_points=input_projection.floor_points,
                ceiling_points=input_projection.ceiling_points,
                projection_confidence=input_projection.confidence,
                projection_warnings=input_projection.warnings,
                projection_model_version=input_projection.model_version,
                projection_normalization_version=input_projection.normalization_version,
                value_score=input_value.value_score,
                value_confidence=input_value.confidence,
                value_uncertainty=input_value.uncertainty,
                market_prior=market_prior,
                value_warnings=input_value.warnings,
                value_version=input_value.value_version,
                value_normalization_version=input_value.normalization_version,
                source_updated_at=prepared_player.source_updated_at,
                feature_version=prepared_player.feature_version,
                dataset_version=prepared_player.dataset_version,
                historical_durability=(
                    current_feature.multi_season_durability
                    or current_feature.durability_rate_8
                    or current_feature.durability_rate_4
                ),
            )
        )
    return CurrentPoolBuild(
        prepared=tuple(prepared),
        recommendation_inputs=tuple(
            sorted(recommendation_inputs, key=lambda item: item.internal_player_id)
        ),
        source_manifest_ids=tuple(
            sorted({current_roster_snapshot.manifest_id, *durability_source_manifest_ids})
        ),
        license_notes=tuple(
            sorted({current_roster_snapshot.license_note, *durability_license_notes})
        ),
    )


def build_current_prepared_pool(
    players: Iterable[CuratedPlayer],
    weeks: Iterable[CuratedWeek],
    current_roster_snapshot: VerifiedSnapshot,
    crosswalk_internal_ids: frozenset[str],
    league: LocalLeagueConfiguration,
    *,
    dataset_version: str,
    target_size: int = 300,
    durability_features: Sequence[DurabilityFeature] = (),
) -> tuple[PreparedPlayer, ...]:
    """Compatibility wrapper for callers that only need prepared baseline rows."""
    return build_current_pool(
        players,
        weeks,
        current_roster_snapshot,
        crosswalk_internal_ids,
        league,
        dataset_version=dataset_version,
        target_size=target_size,
        durability_features=durability_features,
    ).prepared


def publish_current_prepared_pool(
    prepared: Sequence[PreparedPlayer],
    source_snapshots: Sequence[VerifiedSnapshot],
    publication_root: Path,
    *,
    dataset_version: str,
    recommendation_inputs: Sequence[PreparedRecommendationInput] = (),
) -> Path:
    """Stage and atomically publish the base prepared version for crosswalk validation."""
    temporary_root = publication_root / ".current-pool-tmp"
    temporary = temporary_root / f"{dataset_version}.parquet"
    try:
        checksum = write_prepared_parquet(prepared, temporary)
        payload = temporary.read_bytes()
        recommendation_checksum: str | None = None
        recommendation_payload: bytes | None = None
        if recommendation_inputs:
            input_path = temporary_root / f"{dataset_version}-recommendation-inputs.parquet"
            recommendation_checksum = write_prepared_recommendation_inputs_parquet(
                recommendation_inputs, input_path
            )
            recommendation_payload = input_path.read_bytes()
    finally:
        for path in (
            temporary_root.glob(f"{dataset_version}*.parquet") if temporary_root.exists() else ()
        ):
            path.unlink(missing_ok=True)
        temporary_root.rmdir() if temporary_root.exists() and not any(
            temporary_root.iterdir()
        ) else None
    outputs = [OutputFile("prepared.parquet", checksum, len(prepared))]
    files = {"prepared.parquet": payload}
    row_counts = {"prepared.parquet": len(prepared)}
    schemas = {"draftable_assets": "curation-v4", "prepared": "v2"}
    if recommendation_inputs:
        if recommendation_checksum is None or recommendation_payload is None:
            raise DataValidationError("prepared recommendation inputs were not staged")
        prepared_ids = {player.internal_player_id for player in prepared}
        input_ids = {item.internal_player_id for item in recommendation_inputs}
        if prepared_ids != input_ids or any(
            item.dataset_version != dataset_version or item.feature_version != FEATURE_VERSION
            for item in recommendation_inputs
        ):
            raise DataValidationError(
                "prepared recommendation inputs do not match the prepared pool"
            )
        outputs.append(
            OutputFile(
                "prepared_recommendation_inputs.parquet",
                recommendation_checksum,
                len(recommendation_inputs),
            )
        )
        files["prepared_recommendation_inputs.parquet"] = recommendation_payload
        row_counts["prepared_recommendation_inputs.parquet"] = len(recommendation_inputs)
        schemas["prepared_recommendation_inputs"] = "v2"
    manifest = dataset_manifest(
        dataset_version,
        FEATURE_VERSION,
        "current-sleeper-prepared-pool-v1",
        tuple(sorted({snapshot.manifest_id for snapshot in source_snapshots})),
        schemas,
        tuple(outputs),
        {name: True for name in DatasetPublisher.REQUIRED_CHECKS},
        tuple(sorted({snapshot.license_note for snapshot in source_snapshots})),
    )
    return DatasetPublisher(publication_root).publish(manifest, files, row_counts)


def build_and_publish_current_pool(
    assets_path: Path,
    current_roster: VerifiedSnapshot,
    player_stats: Sequence[VerifiedSnapshot],
    pbp: Sequence[VerifiedSnapshot],
    league_config_path: Path,
    crosswalk_report_path: Path,
    publication_root: Path,
    *,
    dataset_version: str,
    target_size: int = 300,
    participation_calendar: VerifiedSnapshot | None = None,
) -> Path:
    """The complete local operation used by the CLI; inputs are all explicit and verified."""
    players = read_curated_players_parquet(assets_path)
    crosswalk_ids = read_crosswalk_internal_ids(crosswalk_report_path, assets_path, season=2026)
    league = read_local_league_configuration(league_config_path)
    weeks = build_historical_weeks(player_stats, pbp)
    durability_features: tuple[DurabilityFeature, ...] = ()
    durability_manifest_ids: tuple[str, ...] = ()
    durability_license_notes: tuple[str, ...] = ()
    if participation_calendar is not None:
        durability_features = build_historical_durability(participation_calendar)
        durability_manifest_ids = (participation_calendar.manifest_id,)
        durability_license_notes = (participation_calendar.license_note,)
    build = build_current_pool(
        players,
        weeks,
        current_roster,
        crosswalk_ids,
        league,
        dataset_version=dataset_version,
        target_size=target_size,
        durability_features=durability_features,
        durability_source_manifest_ids=durability_manifest_ids,
        durability_license_notes=durability_license_notes,
    )
    return publish_current_prepared_pool(
        build.prepared,
        (
            current_roster,
            *player_stats,
            *pbp,
            *((participation_calendar,) if participation_calendar is not None else ()),
        ),
        publication_root,
        dataset_version=dataset_version,
        recommendation_inputs=build.recommendation_inputs,
    )
