"""Local pairing, configuration validation, and loopback API entrypoints."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from nfl_fantasy_assistant.api import create_app
from nfl_fantasy_assistant.config import (
    PairingError,
    TokenStore,
    load_runtime_settings,
)


def main() -> None:
    """Run the narrow local command surface without exposing secrets."""
    parser = argparse.ArgumentParser(description="NFL Fantasy Assistant backend")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate non-secret runtime configuration and local pairing.",
    )
    subparsers = parser.add_subparsers(dest="command")
    pairing_parser = subparsers.add_parser("pair", help="Manage the local backend bearer token.")
    pairing_parser.add_argument("action", choices=("init", "rotate", "revoke"))
    pairing_parser.add_argument(
        "--config-dir",
        type=Path,
        help="Override the private local configuration directory for this command.",
    )
    serve_parser = subparsers.add_parser("serve", help="Run the authenticated loopback API.")
    serve_parser.add_argument("--config-dir", type=Path, help="Private configuration directory.")
    serve_parser.add_argument(
        "--prepared-dataset",
        type=Path,
        help="Checksum-verified immutable Sleeper dataset version to activate at runtime.",
    )
    review_parser = subparsers.add_parser(
        "sleeper-review", help="Review local Sleeper ID candidates."
    )
    review_parser.add_argument("action", choices=("next", "approve", "approve-batch", "status"))
    review_parser.add_argument("--queue", type=Path, required=True)
    review_parser.add_argument("--decisions", type=Path, required=True)
    review_parser.add_argument("--reviewer")
    review_parser.add_argument("--reason")
    review_parser.add_argument("--external-id")
    review_parser.add_argument("--internal-player-id")
    review_parser.add_argument("--confirm", action="store_true")
    crosswalk_parser = subparsers.add_parser(
        "sleeper-crosswalk", help="Validate a versioned local Sleeper identity crosswalk."
    )
    crosswalk_parser.add_argument("action", choices=("validate", "publish"))
    crosswalk_parser.add_argument("--players", type=Path, required=True)
    crosswalk_parser.add_argument("--catalog-manifest", type=Path, required=True)
    crosswalk_parser.add_argument("--catalog-snapshot", type=Path, required=True)
    crosswalk_parser.add_argument("--queue", type=Path, required=True)
    crosswalk_parser.add_argument("--decisions", type=Path, required=True)
    crosswalk_parser.add_argument("--team-transitions", type=Path)
    crosswalk_parser.add_argument(
        "--prepared-dataset",
        type=Path,
        required=True,
        help="Immutable published dataset-version directory containing prepared.parquet.",
    )
    crosswalk_parser.add_argument("--season", type=int, required=True)
    crosswalk_parser.add_argument("--output", type=Path, required=True)
    crosswalk_parser.add_argument(
        "--publication-root",
        type=Path,
        help="Dataset publication root; required for the publish action.",
    )
    crosswalk_parser.add_argument(
        "--dataset-version",
        help="New immutable dataset version; required for the publish action.",
    )
    current_pool_parser = subparsers.add_parser(
        "current-pool", help="Build an immutable current Sleeper prepared-pool dataset."
    )
    current_pool_parser.add_argument("--assets", type=Path, required=True)
    current_pool_parser.add_argument("--current-roster-manifest", type=Path, required=True)
    current_pool_parser.add_argument("--current-roster-snapshot", type=Path, required=True)
    current_pool_parser.add_argument(
        "--player-stats-manifest", type=Path, action="append", required=True
    )
    current_pool_parser.add_argument(
        "--player-stats-snapshot", type=Path, action="append", required=True
    )
    current_pool_parser.add_argument("--pbp-manifest", type=Path, action="append", required=True)
    current_pool_parser.add_argument("--pbp-snapshot", type=Path, action="append", required=True)
    current_pool_parser.add_argument("--league-config", type=Path, required=True)
    current_pool_parser.add_argument("--crosswalk-report", type=Path, required=True)
    current_pool_parser.add_argument("--publication-root", type=Path, required=True)
    current_pool_parser.add_argument("--dataset-version", required=True)
    current_pool_parser.add_argument("--target-size", type=int, default=300)
    arguments = parser.parse_args()

    if arguments.command == "pair":
        store = TokenStore(arguments.config_dir) if arguments.config_dir else TokenStore()
        try:
            if arguments.action == "init":
                token = store.initialize()
                print("Pairing token (displayed once; do not save it in source or a page):")
                print(token)
            elif arguments.action == "rotate":
                token = store.rotate()
                print("New pairing token (re-pair the extension; displayed once):")
                print(token)
            else:
                store.revoke()
                print(
                    "Backend token revoked. The extension must be paired before authenticated use."
                )
        except PairingError as error:
            parser.error(str(error))
        return

    if arguments.command == "serve":
        try:
            from nfl_fantasy_assistant.data.runtime import activate_sleeper_dataset

            config_directory = arguments.config_dir
            runtime = (
                load_runtime_settings(config_directory)
                if config_directory
                else load_runtime_settings()
            )
            token = TokenStore(config_directory).read() if config_directory else TokenStore().read()
            sleeper_dataset = (
                activate_sleeper_dataset(arguments.prepared_dataset)
                if arguments.prepared_dataset
                else None
            )
        except (PairingError, ValueError) as error:
            parser.error(str(error))
        import uvicorn

        uvicorn.run(
            create_app(
                runtime.database_path,
                token,
                runtime.extension_origin,
                sleeper_dataset,
            ),
            host=runtime.backend.host,
            port=runtime.backend.port,
        )
        return

    if arguments.command == "sleeper-review":
        from nfl_fantasy_assistant.data.sleeper_identity import SleeperReviewDecision
        from nfl_fantasy_assistant.data.sleeper_review import (
            batch_review_candidates,
            load_review_decisions,
            load_review_queue,
            next_review_candidate,
            write_review_decisions,
        )

        candidates = load_review_queue(arguments.queue)
        decisions = load_review_decisions(arguments.decisions)
        if arguments.action == "status":
            print(f"Reviewed {len(decisions)} of {len(candidates)} candidates.")
            return
        if arguments.action == "next":
            candidate = next_review_candidate(candidates, decisions)
            if candidate is None:
                print("No candidates remain for review.")
            else:
                print(candidate)
            return
        if arguments.action == "approve-batch":
            if not arguments.reviewer or not arguments.reason:
                parser.error("approve-batch requires --reviewer and --reason")
            batch = batch_review_candidates(candidates, decisions)
            if not arguments.confirm:
                print(
                    f"Would approve {len(batch)} uniquely matched candidates; "
                    "rerun with --confirm to write decisions."
                )
                return
            reviewed_at = datetime.now(UTC).isoformat()
            write_review_decisions(
                (
                    *decisions,
                    *(
                        SleeperReviewDecision(
                            candidate.external_id,
                            candidate.candidate_internal_player_id,
                            arguments.reviewer,
                            reviewed_at,
                            arguments.reason,
                        )
                        for candidate in batch
                    ),
                ),
                arguments.decisions,
            )
            print(f"Approved {len(batch)} eligible Sleeper mapping candidates.")
            return
        candidate = next(
            (row for row in candidates if row.external_id == arguments.external_id), None
        )
        if (
            candidate is None
            or candidate.candidate_internal_player_id != arguments.internal_player_id
        ):
            parser.error("approval must match a queued candidate exactly")
        if not arguments.reviewer or not arguments.reason:
            parser.error("approve requires --reviewer and --reason")
        if any(row.external_id == candidate.external_id for row in decisions):
            parser.error("candidate already has a recorded decision")
        write_review_decisions(
            (
                *decisions,
                SleeperReviewDecision(
                    candidate.external_id,
                    candidate.candidate_internal_player_id,
                    arguments.reviewer,
                    datetime.now(UTC).isoformat(),
                    arguments.reason,
                ),
            ),
            arguments.decisions,
        )
        print("Approved one exact Sleeper mapping candidate.")
        return

    if arguments.command == "sleeper-crosswalk":
        import hashlib
        import json

        from nfl_fantasy_assistant.data.curation import read_curated_players_parquet
        from nfl_fantasy_assistant.data.preparation import read_published_prepared_pool
        from nfl_fantasy_assistant.data.sleeper_identity import (
            SleeperTeamTransitionReview,
            build_approved_sleeper_crosswalk,
            parse_sleeper_catalog,
            publish_sleeper_crosswalk_dataset,
            require_sleeper_coverage,
            require_sleeper_prepared_pool_coverage,
            write_sleeper_crosswalk_report,
        )
        from nfl_fantasy_assistant.data.sleeper_review import (
            load_review_decisions,
            load_review_queue_artifact,
            review_decisions_checksum,
            validate_decisions_against_queue,
        )

        manifest = json.loads(arguments.catalog_manifest.read_text(encoding="utf-8"))
        if (
            manifest.get("source") != "sleeper"
            or manifest.get("dataset") != "players"
            or manifest.get("season") != arguments.season
            or not isinstance(manifest.get("manifest_id"), str)
        ):
            parser.error("catalog manifest is not a Sleeper player catalog for this season")
        catalog_payload = arguments.catalog_snapshot.read_bytes()
        if hashlib.sha256(catalog_payload).hexdigest() != manifest.get("checksum_sha256"):
            parser.error("catalog snapshot checksum does not match its manifest")
        queue = load_review_queue_artifact(arguments.queue)
        if queue.source_manifest_id != manifest["manifest_id"]:
            parser.error("review queue provenance does not match the catalog manifest")
        decisions = validate_decisions_against_queue(
            queue, load_review_decisions(arguments.decisions)
        )
        transitions: tuple[SleeperTeamTransitionReview, ...] = ()
        transition_checksum = None
        if arguments.team_transitions:
            transition_payload = json.loads(arguments.team_transitions.read_text(encoding="utf-8"))
            if not isinstance(transition_payload, dict) or not isinstance(
                transition_payload.get("reviews"), list
            ):
                parser.error("team-transition file must contain a reviews list")
            try:
                transitions = tuple(
                    SleeperTeamTransitionReview(**row) for row in transition_payload["reviews"]
                )
            except TypeError as error:
                parser.error(f"invalid team-transition review: {error}")
            transition_checksum = hashlib.sha256(
                arguments.team_transitions.read_bytes()
            ).hexdigest()
        report = build_approved_sleeper_crosswalk(
            read_curated_players_parquet(arguments.players),
            parse_sleeper_catalog(catalog_payload),
            decisions,
            season=arguments.season,
            source_manifest_id=manifest["manifest_id"],
            review_queue_checksum=queue.checksum,
            review_decisions_checksum=review_decisions_checksum(arguments.decisions),
            player_assets_checksum=hashlib.sha256(arguments.players.read_bytes()).hexdigest(),
            team_transition_reviews=transitions,
            team_transition_checksum=transition_checksum,
        )
        require_sleeper_coverage(
            report,
            (
                *(decision.external_id for decision in decisions),
                *(review.external_id for review in transitions),
            ),
        )
        prepared_pool = read_published_prepared_pool(arguments.prepared_dataset)
        report = require_sleeper_prepared_pool_coverage(
            report,
            prepared_pool.players,
            prepared_pool_checksum=prepared_pool.checksum_sha256,
            prepared_pool_dataset_version=prepared_pool.dataset_version,
            prepared_pool_feature_version=prepared_pool.feature_version,
        )
        published_version = None
        if arguments.action == "publish":
            if not arguments.publication_root or not arguments.dataset_version:
                parser.error("publish requires --publication-root and --dataset-version")
            publication = publish_sleeper_crosswalk_dataset(
                report,
                arguments.prepared_dataset,
                arguments.publication_root,
                dataset_version=arguments.dataset_version,
            )
            report = publication.report
            published_version = publication.version
        checksum = write_sleeper_crosswalk_report(report, arguments.output)
        print(
            f"Validated {len(report.mappings)} mappings; "
            f"{len(report.unresolved_external_ids)} unresolved and "
            f"{len(report.conflict_external_ids)} conflicts. Report checksum: {checksum}."
        )
        if published_version:
            print(f"Published Sleeper crosswalk dataset version: {published_version}.")
        return

    if arguments.command == "current-pool":
        from nfl_fantasy_assistant.data.current_pool import (
            build_and_publish_current_pool,
            read_verified_snapshot,
        )

        if len(arguments.player_stats_manifest) != len(arguments.player_stats_snapshot):
            parser.error("player-stat manifests and snapshots must be paired")
        if len(arguments.pbp_manifest) != len(arguments.pbp_snapshot):
            parser.error("PBP manifests and snapshots must be paired")
        try:
            version = build_and_publish_current_pool(
                arguments.assets,
                read_verified_snapshot(
                    arguments.current_roster_manifest, arguments.current_roster_snapshot
                ),
                tuple(
                    read_verified_snapshot(manifest, snapshot)
                    for manifest, snapshot in zip(
                        arguments.player_stats_manifest,
                        arguments.player_stats_snapshot,
                        strict=True,
                    )
                ),
                tuple(
                    read_verified_snapshot(manifest, snapshot)
                    for manifest, snapshot in zip(
                        arguments.pbp_manifest, arguments.pbp_snapshot, strict=True
                    )
                ),
                arguments.league_config,
                arguments.crosswalk_report,
                arguments.publication_root,
                dataset_version=arguments.dataset_version,
                target_size=arguments.target_size,
            )
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(f"Published current Sleeper prepared-pool dataset version: {version}.")
        return

    if arguments.check_config:
        try:
            settings = load_runtime_settings().backend
            TokenStore().read()
        except PairingError as error:
            parser.error(str(error))
        print(f"Configuration is valid for {settings.host}:{settings.port}.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
