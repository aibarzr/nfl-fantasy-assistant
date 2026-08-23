"""Versioned exact Sleeper catalog-to-asset identity mapping."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from .curation import SUPPORTED_POSITIONS, CuratedPlayer
from .errors import DataValidationError
from .identity import IdentityMapping, internal_player_id
from .preparation import PreparedPlayer, read_published_prepared_pool, write_prepared_parquet
from .publishing import DatasetPublisher, OutputFile, dataset_manifest

SLEEPER_IDENTITY_RULE_VERSION = "1"

SLEEPER_EXTERNAL_ID_SCHEMA = pa.schema(
    [
        ("provider", pa.string()),
        ("external_id", pa.string()),
        ("internal_player_id", pa.string()),
        ("asset_type", pa.string()),
        ("resolution_method", pa.string()),
        ("provenance", pa.string()),
        ("validity_state", pa.string()),
        ("season", pa.int32()),
    ]
)

SLEEPER_COVERAGE_SCHEMA = pa.schema(
    [
        ("provider", pa.string()),
        ("season", pa.int32()),
        ("position", pa.string()),
        ("catalog_total", pa.int32()),
        ("catalog_resolved", pa.int32()),
        ("catalog_blocked", pa.int32()),
        ("prepared_total", pa.int32()),
        ("prepared_resolved", pa.int32()),
        ("prepared_blocked", pa.int32()),
    ]
)


@dataclass(frozen=True, slots=True)
class SleeperCatalogRecord:
    """The narrow catalog shape retained at the identity boundary."""

    external_id: str
    position: str
    nfl_team: str | None
    display_name: str | None = None
    gsis_id: str | None = None
    espn_id: str | None = None

    @classmethod
    def from_mapping(cls, row: Mapping[str, object]) -> SleeperCatalogRecord:
        external_id = str(row.get("player_id") or "")
        position = str(row.get("position") or "").upper()
        if not external_id or position not in SUPPORTED_POSITIONS:
            raise DataValidationError("Sleeper catalog record requires ID and supported position")
        nfl_team = str(row["team"]).upper() if row.get("team") else None
        if position == "DEF" and nfl_team is None:
            raise DataValidationError("Sleeper DEF catalog record requires NFL team")
        return cls(
            external_id=external_id,
            position=position,
            nfl_team=nfl_team,
            display_name=str(row["full_name"]) if row.get("full_name") else None,
            gsis_id=str(row["gsis_id"]) if row.get("gsis_id") else None,
            espn_id=str(row["espn_id"]) if row.get("espn_id") else None,
        )


def parse_sleeper_catalog(payload: bytes) -> tuple[SleeperCatalogRecord, ...]:
    """Decode a locally retained catalog snapshot into the narrow mapping input."""
    try:
        raw_catalog = json.loads(payload)
    except json.JSONDecodeError as error:
        raise DataValidationError("Sleeper catalog payload must be JSON") from error
    if not isinstance(raw_catalog, dict):
        raise DataValidationError("Sleeper catalog payload must be an object keyed by player ID")
    records: list[SleeperCatalogRecord] = []
    for external_id, raw_record in raw_catalog.items():
        if not isinstance(external_id, str) or not isinstance(raw_record, dict):
            raise DataValidationError("Sleeper catalog has an invalid entry")
        declared_id = raw_record.get("player_id")
        if declared_id is not None and str(declared_id) != external_id:
            raise DataValidationError("Sleeper catalog key conflicts with player_id")
        if str(raw_record.get("position") or "").upper() not in SUPPORTED_POSITIONS:
            continue
        records.append(SleeperCatalogRecord.from_mapping({"player_id": external_id, **raw_record}))
    return tuple(sorted(records, key=lambda record: record.external_id))


@dataclass(frozen=True, slots=True)
class SleeperCrosswalkReport:
    source_manifest_id: str
    season: int
    mappings: tuple[IdentityMapping, ...]
    unresolved_external_ids: tuple[str, ...]
    conflict_external_ids: tuple[str, ...]
    coverage_by_position: dict[str, tuple[int, int, int]]
    review_queue_checksum: str | None = None
    review_decisions_checksum: str | None = None
    player_assets_checksum: str | None = None
    team_transition_checksum: str | None = None
    prepared_pool_coverage: dict[str, tuple[int, int, int]] | None = None
    prepared_pool_checksum: str | None = None
    prepared_pool_dataset_version: str | None = None
    prepared_pool_feature_version: str | None = None


@dataclass(frozen=True, slots=True)
class SleeperCrosswalkPublication:
    """A report re-pinned to the immutable dataset version that contains its mapping table."""

    version: Path
    report: SleeperCrosswalkReport


@dataclass(frozen=True, slots=True)
class SleeperReviewCandidate:
    external_id: str
    candidate_internal_player_id: str
    position: str
    nfl_team: str | None
    provider_display_name: str
    internal_display_name: str
    batch_eligible: bool


@dataclass(frozen=True, slots=True)
class SleeperReviewDecision:
    external_id: str
    internal_player_id: str
    reviewer: str
    reviewed_at: str
    reason: str


@dataclass(frozen=True, slots=True)
class SleeperTeamTransitionReview:
    external_id: str
    internal_player_id: str
    prior_nfl_team: str
    current_nfl_team: str
    reviewer: str
    reviewed_at: str
    reason: str


def build_sleeper_crosswalk(
    players: Iterable[CuratedPlayer],
    catalog: Iterable[SleeperCatalogRecord],
    *,
    season: int,
    source_manifest_id: str,
) -> SleeperCrosswalkReport:
    """Build exact mappings only; catalog names are intentionally absent from this API."""
    if season < 2000:
        raise DataValidationError("Sleeper crosswalk requires a valid NFL season")
    if not source_manifest_id:
        raise DataValidationError("Sleeper crosswalk requires source manifest provenance")

    assets = tuple(players)
    by_gsis: dict[str, list[CuratedPlayer]] = defaultdict(list)
    by_espn: dict[str, list[CuratedPlayer]] = defaultdict(list)
    defenses_by_team: dict[str, list[CuratedPlayer]] = defaultdict(list)
    for player in assets:
        if player.gsis_id:
            by_gsis[player.gsis_id].append(player)
        if player.espn_id:
            by_espn[player.espn_id].append(player)
        if player.position == "DEF" and player.nfl_team:
            defenses_by_team[player.nfl_team].append(player)

    mappings: list[IdentityMapping] = []
    unresolved: list[str] = []
    conflicts: list[str] = []
    seen_external_ids: set[str] = set()
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for record in catalog:
        if record.external_id in seen_external_ids:
            raise DataValidationError("Sleeper catalog contains duplicate external ID")
        seen_external_ids.add(record.external_id)
        counts[record.position][0] += 1
        candidates: set[CuratedPlayer] = set()
        if record.position == "DEF":
            candidates.update(
                player
                for player in defenses_by_team.get(record.nfl_team or "", ())
                if (player.valid_from_season is None or player.valid_from_season <= season)
                and (player.valid_through_season is None or season <= player.valid_through_season)
            )
            method = f"sleeper_defense_team_v{SLEEPER_IDENTITY_RULE_VERSION}"
            identifier_conflict = False
        else:
            identifier_candidates: list[set[CuratedPlayer]] = []
            if record.gsis_id:
                identifier_candidates.append(set(by_gsis.get(record.gsis_id, ())))
            if record.espn_id:
                identifier_candidates.append(set(by_espn.get(record.espn_id, ())))
            if identifier_candidates and all(identifier_candidates):
                candidates = set.intersection(*identifier_candidates)
            method = f"sleeper_exact_identifier_v{SLEEPER_IDENTITY_RULE_VERSION}"
            identifier_conflict = (
                len(identifier_candidates) > 1 and all(identifier_candidates) and not candidates
            )

        candidates = {
            player
            for player in candidates
            if player.position == record.position and player.nfl_team == record.nfl_team
        }
        if len(candidates) == 1:
            player = next(iter(candidates))
            mappings.append(
                IdentityMapping(
                    provider="sleeper",
                    external_id=record.external_id,
                    internal_player_id=internal_player_id(player),
                    method=method,
                    provenance=f"sleeper_catalog:{source_manifest_id}",
                    asset_type=player.asset_type,
                )
            )
            counts[record.position][1] += 1
        elif identifier_conflict or len(candidates) > 1:
            conflicts.append(record.external_id)
            counts[record.position][2] += 1
        else:
            unresolved.append(record.external_id)
            counts[record.position][2] += 1
    return SleeperCrosswalkReport(
        source_manifest_id=source_manifest_id,
        season=season,
        mappings=tuple(sorted(mappings, key=lambda mapping: mapping.external_id)),
        unresolved_external_ids=tuple(sorted(unresolved)),
        conflict_external_ids=tuple(sorted(conflicts)),
        coverage_by_position={
            position: (count[0], count[1], count[2]) for position, count in sorted(counts.items())
        },
    )


def require_sleeper_coverage(
    report: SleeperCrosswalkReport, required_external_ids: Iterable[str]
) -> None:
    mapped = {mapping.external_id for mapping in report.mappings}
    missing = sorted(set(required_external_ids) - mapped)
    if missing:
        raise DataValidationError("required Sleeper references are unresolved or conflicting")


def require_sleeper_prepared_pool_coverage(
    report: SleeperCrosswalkReport,
    prepared_pool: Iterable[PreparedPlayer],
    *,
    prepared_pool_checksum: str,
    prepared_pool_dataset_version: str,
    prepared_pool_feature_version: str,
) -> SleeperCrosswalkReport:
    """Attach coverage for the actual published pool and reject any unmapped asset."""
    if not all(
        (prepared_pool_checksum, prepared_pool_dataset_version, prepared_pool_feature_version)
    ):
        raise DataValidationError("prepared pool coverage requires checksum and dataset versions")
    prepared = tuple(prepared_pool)
    mapped_ids = {mapping.internal_player_id for mapping in report.mappings}
    missing = sorted(
        player.internal_player_id
        for player in prepared
        if player.internal_player_id not in mapped_ids
    )
    if missing:
        raise DataValidationError("prepared pool contains Sleeper-unmapped assets")
    coverage: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for player in prepared:
        coverage[player.position][0] += 1
        coverage[player.position][1] += 1
    return SleeperCrosswalkReport(
        source_manifest_id=report.source_manifest_id,
        season=report.season,
        mappings=report.mappings,
        unresolved_external_ids=report.unresolved_external_ids,
        conflict_external_ids=report.conflict_external_ids,
        coverage_by_position=report.coverage_by_position,
        review_queue_checksum=report.review_queue_checksum,
        review_decisions_checksum=report.review_decisions_checksum,
        player_assets_checksum=report.player_assets_checksum,
        team_transition_checksum=report.team_transition_checksum,
        prepared_pool_coverage={
            position: (counts[0], counts[1], counts[2])
            for position, counts in sorted(coverage.items())
        },
        prepared_pool_checksum=prepared_pool_checksum,
        prepared_pool_dataset_version=prepared_pool_dataset_version,
        prepared_pool_feature_version=prepared_pool_feature_version,
    )


def build_approved_sleeper_crosswalk(
    players: Iterable[CuratedPlayer],
    catalog: Iterable[SleeperCatalogRecord],
    decisions: Iterable[SleeperReviewDecision],
    team_transition_reviews: Iterable[SleeperTeamTransitionReview] = (),
    *,
    season: int,
    source_manifest_id: str,
    review_queue_checksum: str,
    review_decisions_checksum: str,
    player_assets_checksum: str,
    team_transition_checksum: str | None = None,
) -> SleeperCrosswalkReport:
    """Merge reviewed mappings only where they cannot contradict exact catalog evidence."""
    if not all((review_queue_checksum, review_decisions_checksum, player_assets_checksum)):
        raise DataValidationError("approved Sleeper crosswalk requires complete input checksums")
    assets = tuple(players)
    records = tuple(catalog)
    exact = build_sleeper_crosswalk(
        assets, records, season=season, source_manifest_id=source_manifest_id
    )
    reviewed = approve_sleeper_review_decisions(
        assets,
        records,
        decisions,
        season=season,
        source_manifest_id=source_manifest_id,
    )
    transitions = approve_sleeper_team_transition_reviews(
        assets,
        records,
        team_transition_reviews,
        season=season,
        source_manifest_id=source_manifest_id,
    )
    reviewed = (*reviewed, *transitions)
    if len({mapping.external_id for mapping in reviewed}) != len(reviewed):
        raise DataValidationError("Sleeper review inputs contain duplicate external IDs")
    mappings = {mapping.external_id: mapping for mapping in exact.mappings}
    unresolved = set(exact.unresolved_external_ids)
    conflicts = set(exact.conflict_external_ids)
    for mapping in reviewed:
        existing = mappings.get(mapping.external_id)
        if mapping.external_id in conflicts:
            raise DataValidationError("review decision cannot override a catalog identity conflict")
        if existing is not None:
            if existing.internal_player_id != mapping.internal_player_id:
                raise DataValidationError("review decision conflicts with exact catalog mapping")
            continue
        if mapping.external_id not in unresolved:
            raise DataValidationError("review decision has no unresolved Sleeper reference")
        mappings[mapping.external_id] = mapping
        unresolved.remove(mapping.external_id)

    coverage: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for record in records:
        coverage[record.position][0] += 1
        if record.external_id in mappings:
            coverage[record.position][1] += 1
        else:
            coverage[record.position][2] += 1
    return SleeperCrosswalkReport(
        source_manifest_id=source_manifest_id,
        season=season,
        mappings=tuple(sorted(mappings.values(), key=lambda mapping: mapping.external_id)),
        unresolved_external_ids=tuple(sorted(unresolved)),
        conflict_external_ids=tuple(sorted(conflicts)),
        coverage_by_position={
            position: (count[0], count[1], count[2]) for position, count in sorted(coverage.items())
        },
        review_queue_checksum=review_queue_checksum,
        review_decisions_checksum=review_decisions_checksum,
        player_assets_checksum=player_assets_checksum,
        team_transition_checksum=team_transition_checksum,
    )


def propose_sleeper_review_candidates(
    players: Iterable[CuratedPlayer], catalog: Iterable[SleeperCatalogRecord]
) -> tuple[SleeperReviewCandidate, ...]:
    """Suggest one-to-one name/team/position candidates without accepting any mapping."""
    assets = tuple(players)
    candidates: list[SleeperReviewCandidate] = []
    for record in catalog:
        if record.position == "DEF" or not record.display_name:
            continue
        matches = [
            player
            for player in assets
            if player.position == record.position
            and player.nfl_team == record.nfl_team
            and player.display_name.casefold() == record.display_name.casefold()
        ]
        if len(matches) == 1:
            player = matches[0]
            candidates.append(
                SleeperReviewCandidate(
                    external_id=record.external_id,
                    candidate_internal_player_id=internal_player_id(player),
                    position=record.position,
                    nfl_team=record.nfl_team,
                    provider_display_name=record.display_name,
                    internal_display_name=player.display_name,
                    batch_eligible=record.gsis_id is None and record.espn_id is None,
                )
            )
    return tuple(sorted(candidates, key=lambda candidate: candidate.external_id))


def approve_sleeper_review_decisions(
    players: Iterable[CuratedPlayer],
    catalog: Iterable[SleeperCatalogRecord],
    decisions: Iterable[SleeperReviewDecision],
    *,
    season: int,
    source_manifest_id: str,
) -> tuple[IdentityMapping, ...]:
    """Turn explicit human decisions into exact provider mappings after consistency checks."""
    assets = {internal_player_id(player): player for player in players}
    records = {record.external_id: record for record in catalog}
    accepted: list[IdentityMapping] = []
    seen: set[str] = set()
    for decision in decisions:
        if not decision.reviewer or not decision.reviewed_at or not decision.reason:
            raise DataValidationError("review decisions require reviewer, timestamp, and reason")
        if decision.external_id in seen:
            raise DataValidationError("duplicate Sleeper review decision")
        seen.add(decision.external_id)
        record = records.get(decision.external_id)
        player = assets.get(decision.internal_player_id)
        if record is None or player is None:
            raise DataValidationError("review decision references an unknown asset")
        if player.position != record.position or player.nfl_team != record.nfl_team:
            raise DataValidationError("review decision conflicts with position or NFL team")
        if record.position == "DEF" and (
            (player.valid_from_season is not None and season < player.valid_from_season)
            or (player.valid_through_season is not None and season > player.valid_through_season)
        ):
            raise DataValidationError("review decision is outside team-defense validity period")
        accepted.append(
            IdentityMapping(
                provider="sleeper",
                external_id=record.external_id,
                internal_player_id=decision.internal_player_id,
                method=f"sleeper_reviewed_override_v{SLEEPER_IDENTITY_RULE_VERSION}",
                provenance=(
                    f"sleeper_review:{source_manifest_id}:{decision.reviewer}:{decision.reviewed_at}"
                ),
                asset_type=player.asset_type,
            )
        )
    return tuple(sorted(accepted, key=lambda mapping: mapping.external_id))


def approve_sleeper_team_transition_reviews(
    players: Iterable[CuratedPlayer],
    catalog: Iterable[SleeperCatalogRecord],
    reviews: Iterable[SleeperTeamTransitionReview],
    *,
    season: int,
    source_manifest_id: str,
) -> tuple[IdentityMapping, ...]:
    """Accept an auditable reviewer decision for a current-team source disagreement."""
    assets = {internal_player_id(player): player for player in players}
    records = {record.external_id: record for record in catalog}
    accepted: list[IdentityMapping] = []
    seen: set[str] = set()
    for review in reviews:
        if not review.reviewer or not review.reviewed_at or not review.reason:
            raise DataValidationError(
                "team-transition review requires reviewer, timestamp, and reason"
            )
        if review.external_id in seen:
            raise DataValidationError("duplicate Sleeper team-transition review")
        seen.add(review.external_id)
        record = records.get(review.external_id)
        player = assets.get(review.internal_player_id)
        if record is None or player is None:
            raise DataValidationError("team-transition review references an unknown asset")
        if (
            record.position == "DEF"
            or player.position != record.position
            or player.nfl_team != review.prior_nfl_team
            or record.nfl_team != review.current_nfl_team
            or review.prior_nfl_team == review.current_nfl_team
        ):
            raise DataValidationError(
                "team-transition review does not match the observed team change"
            )
        accepted.append(
            IdentityMapping(
                provider="sleeper",
                external_id=record.external_id,
                internal_player_id=review.internal_player_id,
                method=f"sleeper_reviewed_team_transition_v{SLEEPER_IDENTITY_RULE_VERSION}",
                provenance=(
                    f"sleeper_team_transition:{source_manifest_id}:"
                    f"{review.reviewer}:{review.reviewed_at}"
                ),
                asset_type=player.asset_type,
            )
        )
    return tuple(sorted(accepted, key=lambda mapping: mapping.external_id))


def write_sleeper_review_queue(
    candidates: Iterable[SleeperReviewCandidate], path: Path, *, source_manifest_id: str
) -> str:
    """Write a deterministic local-only queue; it contains suggestions, never mappings."""
    if not source_manifest_id:
        raise DataValidationError("Sleeper review queue requires source manifest provenance")
    payload = {
        "schema_version": "1",
        "status": "requires_explicit_review",
        "source_manifest_id": source_manifest_id,
        "candidates": [
            {
                "external_id": candidate.external_id,
                "candidate_internal_player_id": candidate.candidate_internal_player_id,
                "position": candidate.position,
                "nfl_team": candidate.nfl_team,
                "provider_display_name": candidate.provider_display_name,
                "internal_display_name": candidate.internal_display_name,
                "batch_eligible": candidate.batch_eligible,
            }
            for candidate in sorted(candidates, key=lambda candidate: candidate.external_id)
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return hashlib.sha256(serialized.encode()).hexdigest()


def write_sleeper_crosswalk_report(report: SleeperCrosswalkReport, path: Path) -> str:
    """Persist a deterministic, local-only crosswalk/report artifact for a dataset version."""
    payload = {
        "schema_version": "1",
        "provider": "sleeper",
        "identity_rule_version": SLEEPER_IDENTITY_RULE_VERSION,
        "source_manifest_id": report.source_manifest_id,
        "season": report.season,
        "mappings": [
            {
                "external_id": mapping.external_id,
                "internal_player_id": mapping.internal_player_id,
                "method": mapping.method,
                "provenance": mapping.provenance,
                "asset_type": mapping.asset_type,
            }
            for mapping in report.mappings
        ],
        "unresolved_external_ids": list(report.unresolved_external_ids),
        "conflict_external_ids": list(report.conflict_external_ids),
        "coverage_by_position": {
            position: {"total": total, "resolved": resolved, "blocked": blocked}
            for position, (total, resolved, blocked) in report.coverage_by_position.items()
        },
        "input_checksums": {
            "review_queue": report.review_queue_checksum,
            "review_decisions": report.review_decisions_checksum,
            "player_assets": report.player_assets_checksum,
            "team_transitions": report.team_transition_checksum,
        },
        "prepared_pool_coverage": (
            None
            if report.prepared_pool_coverage is None
            else {
                position: {"total": total, "resolved": resolved, "blocked": blocked}
                for position, (total, resolved, blocked) in report.prepared_pool_coverage.items()
            }
        ),
        "prepared_pool_checksum": report.prepared_pool_checksum,
        "prepared_pool_dataset_version": report.prepared_pool_dataset_version,
        "prepared_pool_feature_version": report.prepared_pool_feature_version,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return hashlib.sha256(serialized.encode()).hexdigest()


def _parquet_bytes(rows: list[dict[str, object]], schema: pa.Schema) -> bytes:
    sink = pa.BufferOutputStream()
    pq.write_table(
        pa.Table.from_pylist(rows, schema=schema), sink, compression="zstd", version="2.6"
    )
    return bytes(sink.getvalue().to_pybytes())


def publish_sleeper_crosswalk_dataset(
    report: SleeperCrosswalkReport,
    prepared_dataset_version: Path,
    publication_root: Path,
    *,
    dataset_version: str,
) -> SleeperCrosswalkPublication:
    """Derive a new immutable dataset version that includes validated Sleeper identity evidence.

    Dataset versions are immutable.  Rather than modifying the prepared version that was used for
    validation, this function copies its declared outputs, re-pins ``prepared.parquet`` to a new
    version, and adds canonical ``asset_external_ids`` plus coverage evidence.  It cannot publish
    an unchecked report or overwrite an existing identity table.
    """
    parent = read_published_prepared_pool(prepared_dataset_version)
    if not dataset_version or dataset_version == parent.dataset_version:
        raise DataValidationError("Sleeper crosswalk publication requires a new dataset version")
    if (
        report.prepared_pool_checksum != parent.checksum_sha256
        or report.prepared_pool_dataset_version != parent.dataset_version
        or report.prepared_pool_feature_version != parent.feature_version
        or report.prepared_pool_coverage is None
    ):
        raise DataValidationError("crosswalk report is not pinned to the supplied prepared dataset")
    inherited_outputs = {output.relative_path for output in parent.manifest.outputs}
    additions = {"asset_external_ids.parquet", "sleeper_crosswalk_coverage.parquet"}
    if inherited_outputs & additions:
        raise DataValidationError(
            "prepared dataset already has Sleeper crosswalk publication outputs"
        )
    if len({mapping.external_id for mapping in report.mappings}) != len(report.mappings):
        raise DataValidationError("Sleeper crosswalk has duplicate provider external IDs")

    repinned_players = tuple(
        PreparedPlayer(
            internal_player_id=player.internal_player_id,
            position=player.position,
            baseline_score=player.baseline_score,
            source_updated_at=player.source_updated_at,
            feature_version=parent.feature_version,
            dataset_version=dataset_version,
        )
        for player in parent.players
    )
    prepared_path = publication_root / ".sleeper-crosswalk-tmp" / f"{dataset_version}.parquet"
    try:
        prepared_checksum = write_prepared_parquet(repinned_players, prepared_path)
        published_report = require_sleeper_prepared_pool_coverage(
            report,
            repinned_players,
            prepared_pool_checksum=prepared_checksum,
            prepared_pool_dataset_version=dataset_version,
            prepared_pool_feature_version=parent.feature_version,
        )
        coverage = published_report.prepared_pool_coverage
        assert coverage is not None
        files = {
            output.relative_path: (
                prepared_path.read_bytes()
                if output.relative_path == "prepared.parquet"
                else (prepared_dataset_version / output.relative_path).read_bytes()
            )
            for output in parent.manifest.outputs
        }
        files["asset_external_ids.parquet"] = _parquet_bytes(
            [
                {
                    "provider": mapping.provider,
                    "external_id": mapping.external_id,
                    "internal_player_id": mapping.internal_player_id,
                    "asset_type": mapping.asset_type,
                    "resolution_method": mapping.method,
                    "provenance": mapping.provenance,
                    "validity_state": "resolved",
                    "season": published_report.season,
                }
                for mapping in published_report.mappings
            ],
            SLEEPER_EXTERNAL_ID_SCHEMA,
        )
        files["sleeper_crosswalk_coverage.parquet"] = _parquet_bytes(
            [
                {
                    "provider": "sleeper",
                    "season": published_report.season,
                    "position": position,
                    "catalog_total": catalog[0],
                    "catalog_resolved": catalog[1],
                    "catalog_blocked": catalog[2],
                    "prepared_total": coverage.get(position, (0, 0, 0))[0],
                    "prepared_resolved": coverage.get(position, (0, 0, 0))[1],
                    "prepared_blocked": coverage.get(position, (0, 0, 0))[2],
                }
                for position, catalog in sorted(published_report.coverage_by_position.items())
            ],
            SLEEPER_COVERAGE_SCHEMA,
        )
        row_counts = {output.relative_path: output.row_count for output in parent.manifest.outputs}
        row_counts["prepared.parquet"] = len(repinned_players)
        row_counts["asset_external_ids.parquet"] = len(published_report.mappings)
        row_counts["sleeper_crosswalk_coverage.parquet"] = len(
            published_report.coverage_by_position
        )
        outputs = tuple(
            OutputFile(name, hashlib.sha256(payload).hexdigest(), row_counts[name])
            for name, payload in sorted(files.items())
        )
        schemas = dict(parent.manifest.schemas)
        schemas.update(
            {
                "asset_external_ids": "sleeper-v1",
                "sleeper_crosswalk_coverage": "v1",
            }
        )
        manifest = dataset_manifest(
            dataset_version,
            parent.feature_version,
            f"{parent.manifest.transform_revision}+sleeper-crosswalk-v1",
            tuple(sorted({*parent.manifest.source_manifest_ids, report.source_manifest_id})),
            schemas,
            outputs,
            dict(parent.manifest.validation),
            tuple(sorted({*parent.manifest.license_notes, "Sleeper non-commercial API"})),
        )
        version = DatasetPublisher(publication_root).publish(manifest, files, row_counts)
        return SleeperCrosswalkPublication(version=version, report=published_report)
    finally:
        prepared_path.unlink(missing_ok=True)
        if prepared_path.parent.exists():
            try:
                prepared_path.parent.rmdir()
            except OSError:
                pass
