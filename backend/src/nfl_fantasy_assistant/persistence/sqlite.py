"""SQLite implementation of application persistence ports and immutable migrations."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    DraftPick,
    DraftSession,
    DraftStatus,
    IdentityState,
    LeagueConfig,
    LeagueId,
    Player,
    PlayerReference,
    RecommendationCandidate,
    RecommendationSnapshot,
    ReconciliationState,
    RosterSlot,
    UnresolvedObservation,
)


class PersistenceError(RuntimeError):
    """A safe, non-secret persistence failure suitable for application error mapping."""


MIGRATIONS_DIRECTORY = Path(__file__).with_name("migrations")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _config_to_json(config: LeagueConfig) -> str:
    return _json(
        {
            "config_version": config.config_version,
            "team_count": config.team_count,
            "draft_type": config.draft_type,
            "roster_slots": [
                {
                    "name": slot.name,
                    "eligible_positions": sorted(slot.eligible_positions),
                    "is_bench": slot.is_bench,
                }
                for slot in config.roster_slots
            ],
            "scoring_rules": dict(config.scoring_rules),
            "superflex": config.superflex,
            "te_premium": config.te_premium,
        }
    )


def _config_from_json(value: str) -> LeagueConfig:
    raw = json.loads(value)
    return LeagueConfig(
        config_version=raw["config_version"],
        team_count=raw["team_count"],
        draft_type=raw["draft_type"],
        roster_slots=tuple(
            RosterSlot(slot["name"], frozenset(slot["eligible_positions"]), slot["is_bench"])
            for slot in raw["roster_slots"]
        ),
        scoring_rules=raw["scoring_rules"],
        superflex=raw["superflex"],
        te_premium=raw["te_premium"],
    )


def _player_to_json(player: Player) -> str:
    return _json(
        {
            "internal_player_id": player.internal_player_id,
            "external_ids": dict(player.external_ids),
            "display_name": player.display_name,
            "position": player.position,
            "nfl_team": player.nfl_team,
            "identity_state": player.identity_state.value,
        }
    )


def _player_from_json(value: str) -> Player:
    raw = json.loads(value)
    return Player(
        internal_player_id=raw["internal_player_id"],
        external_ids=raw["external_ids"],
        display_name=raw["display_name"],
        position=raw["position"],
        nfl_team=raw["nfl_team"],
        identity_state=IdentityState(raw["identity_state"]),
    )


def _unresolved_to_json(observation: UnresolvedObservation) -> str:
    return _json(
        {
            "event_id": observation.event_id,
            "overall_pick": observation.overall_pick,
            "team_id": observation.team_id,
            "reference": asdict(observation.reference),
            "source": observation.source,
            "observed_at": observation.observed_at.isoformat(),
            "reason": observation.reason,
        }
    )


def _unresolved_from_json(value: str) -> UnresolvedObservation:
    raw = json.loads(value)
    return UnresolvedObservation(
        event_id=raw["event_id"],
        overall_pick=raw["overall_pick"],
        team_id=raw["team_id"],
        reference=PlayerReference(**raw["reference"]),
        source=raw["source"],
        observed_at=datetime.fromisoformat(raw["observed_at"]),
        reason=raw["reason"],
    )


def _snapshot_to_json(snapshot: RecommendationSnapshot) -> str:
    return _json(
        {
            "snapshot_id": snapshot.snapshot_id,
            "draft_id": snapshot.draft_id.value,
            "canonical_revision": snapshot.canonical_revision,
            "generated_at": snapshot.generated_at.isoformat(),
            "available_player_ids": snapshot.available_player_ids,
            "candidates": [
                {
                    "internal_player_id": candidate.internal_player_id,
                    "rank": candidate.rank,
                    "draft_score": candidate.draft_score,
                    "confidence": candidate.confidence,
                    "components": dict(candidate.components),
                    "reason_codes": candidate.reason_codes,
                    "reason_text": candidate.reason_text,
                    "warnings": candidate.warnings,
                }
                for candidate in snapshot.candidates
            ],
            "config_version": snapshot.config_version,
            "dataset_version": snapshot.dataset_version,
            "feature_version": snapshot.feature_version,
            "model_version": snapshot.model_version,
            "source_updated_at": dict(snapshot.source_updated_at),
            "is_current": snapshot.is_current,
            "chosen_player_id": snapshot.chosen_player_id,
        }
    )


def _snapshot_from_json(value: str) -> RecommendationSnapshot:
    raw = json.loads(value)
    return RecommendationSnapshot(
        snapshot_id=raw["snapshot_id"],
        draft_id=DraftId(raw["draft_id"]),
        canonical_revision=raw["canonical_revision"],
        generated_at=datetime.fromisoformat(raw["generated_at"]),
        available_player_ids=tuple(raw["available_player_ids"]),
        candidates=tuple(
            RecommendationCandidate(
                internal_player_id=candidate["internal_player_id"],
                rank=candidate["rank"],
                draft_score=candidate["draft_score"],
                confidence=candidate["confidence"],
                components=candidate["components"],
                reason_codes=tuple(candidate["reason_codes"]),
                reason_text=candidate["reason_text"],
                warnings=tuple(candidate.get("warnings", ())),
            )
            for candidate in raw["candidates"]
        ),
        config_version=raw["config_version"],
        dataset_version=raw["dataset_version"],
        feature_version=raw["feature_version"],
        model_version=raw["model_version"],
        source_updated_at=raw["source_updated_at"],
        is_current=raw["is_current"],
        chosen_player_id=raw["chosen_player_id"],
    )


class MigrationManager:
    """Applies ordered, append-only SQL migrations in one transaction each."""

    def __init__(self, directory: Path = MIGRATIONS_DIRECTORY) -> None:
        self._directory = directory

    def apply(self, connection: sqlite3.Connection) -> None:
        files = sorted(self._directory.glob("[0-9][0-9][0-9]_*.sql"))
        expected = list(range(1, len(files) + 1))
        versions = [int(path.name[:3]) for path in files]
        if versions != expected:
            raise PersistenceError("migration versions must be consecutive and immutable")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        applied = {
            int(row[0]) for row in connection.execute("SELECT version FROM schema_migrations")
        }
        unknown = applied - set(versions)
        if unknown:
            raise PersistenceError("database contains a migration unknown to this application")
        for path, version in zip(files, versions, strict=True):
            if version in applied:
                continue
            try:
                with connection:
                    connection.executescript(path.read_text(encoding="utf-8"))
                    connection.execute(
                        "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                        (version, _timestamp()),
                    )
            except sqlite3.DatabaseError as error:
                raise PersistenceError("database migration failed without being applied") from error


class SqliteDraftRepository:
    """Parameterized SQLite adapter for canonical draft state and reproducible history."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path.resolve()
        if self._database_path.name in {"", ".", "/"}:
            raise PersistenceError("database path must identify one database file")
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        # The local ASGI test/runtime lifecycle may construct and close the app on different
        # threads. Request processing remains serialized by this synchronous repository.
        self._connection = sqlite3.connect(
            self._database_path, isolation_level=None, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self.migrate()

    def close(self) -> None:
        self._connection.close()

    def migrate(self) -> None:
        MigrationManager().apply(self._connection)

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            yield self._connection
            self._connection.execute("COMMIT")
        except Exception:
            self._connection.execute("ROLLBACK")
            raise

    def save_player(self, player: Player) -> None:
        try:
            with self._transaction() as connection:
                for provider, external_id in player.external_ids.items():
                    mapped = connection.execute(
                        "SELECT internal_player_id FROM player_external_ids "
                        "WHERE provider = ? AND external_id = ?",
                        (provider, external_id),
                    ).fetchone()
                    if mapped is not None and mapped[0] != player.internal_player_id:
                        raise PersistenceError(
                            "external player identity is already mapped differently"
                        )
                connection.execute(
                    "INSERT INTO players(internal_player_id, player_json) VALUES (?, ?) "
                    "ON CONFLICT(internal_player_id) DO UPDATE SET "
                    "player_json = excluded.player_json",
                    (player.internal_player_id, _player_to_json(player)),
                )
                connection.executemany(
                    "INSERT INTO player_external_ids(provider, external_id, internal_player_id) "
                    "VALUES (?, ?, ?) "
                    "ON CONFLICT(provider, external_id) DO NOTHING",
                    [
                        (provider, external_id, player.internal_player_id)
                        for provider, external_id in player.external_ids.items()
                    ],
                )
        except sqlite3.DatabaseError as error:
            raise PersistenceError("could not persist player identity") from error

    def get_player(self, internal_player_id: str) -> Player | None:
        row = self._connection.execute(
            "SELECT player_json FROM players WHERE internal_player_id = ?", (internal_player_id,)
        ).fetchone()
        return _player_from_json(row[0]) if row is not None else None

    def find_player_by_external_id(self, provider: str, external_id: str) -> Player | None:
        row = self._connection.execute(
            "SELECT p.player_json FROM players p JOIN player_external_ids e "
            "ON e.internal_player_id = p.internal_player_id "
            "WHERE e.provider = ? AND e.external_id = ?",
            (provider, external_id),
        ).fetchone()
        return _player_from_json(row[0]) if row is not None else None

    def save_draft(self, session: DraftSession) -> None:
        try:
            with self._transaction() as connection:
                self._write_session(connection, session)
        except sqlite3.DatabaseError as error:
            raise PersistenceError("could not persist canonical draft state") from error

    def find_league_by_provider(self, provider: str, provider_league_id: str) -> LeagueId | None:
        row = self._connection.execute(
            "SELECT league_id FROM league_provider_refs WHERE provider = ? "
            "AND provider_league_id = ?",
            (provider, provider_league_id),
        ).fetchone()
        return LeagueId(row["league_id"]) if row is not None else None

    def save_league_identity(
        self, league_id: LeagueId, provider: str, provider_league_id: str, config: LeagueConfig
    ) -> None:
        if not provider or not provider_league_id:
            raise PersistenceError("provider league identity must be non-empty")
        try:
            with self._transaction() as connection:
                config_json = _config_to_json(config)
                existing = connection.execute(
                    "SELECT league_id FROM league_provider_refs "
                    "WHERE provider = ? AND provider_league_id = ?",
                    (provider, provider_league_id),
                ).fetchone()
                if existing is not None and existing["league_id"] != league_id.value:
                    raise PersistenceError("provider league identity is already bound")
                existing_config = connection.execute(
                    "SELECT config_json FROM leagues WHERE league_id = ?", (league_id.value,)
                ).fetchone()
                if existing_config is not None and existing_config["config_json"] != config_json:
                    raise PersistenceError("active league configuration is immutable")
                connection.execute(
                    "INSERT INTO leagues(league_id, config_version, config_json, created_at) "
                    "VALUES (?, ?, ?, ?) ON CONFLICT(league_id) DO NOTHING",
                    (league_id.value, config.config_version, config_json, _timestamp()),
                )
                if existing is None:
                    connection.execute(
                        "INSERT INTO league_provider_refs(provider, provider_league_id, league_id) "
                        "VALUES (?, ?, ?)",
                        (provider, provider_league_id, league_id.value),
                    )
        except sqlite3.IntegrityError as error:
            raise PersistenceError("could not persist provider league identity") from error

    def commit_transition(
        self,
        session: DraftSession,
        event_id: str | None = None,
        fingerprint: str | None = None,
        outcome: str | None = None,
    ) -> None:
        if (event_id, fingerprint, outcome).count(None) not in {0, 3}:
            raise PersistenceError("an event commit needs ID, fingerprint, and outcome together")
        try:
            with self._transaction() as connection:
                self._write_session(connection, session)
                if event_id is not None and fingerprint is not None and outcome is not None:
                    connection.execute(
                        "INSERT INTO event_outcomes(draft_id, event_id, fingerprint, outcome, "
                        "resulting_revision) VALUES (?, ?, ?, ?, ?)",
                        (session.draft_id.value, event_id, fingerprint, outcome, session.revision),
                    )
        except sqlite3.IntegrityError as error:
            raise PersistenceError(
                "state transition conflicts with persisted canonical state"
            ) from error
        except sqlite3.DatabaseError as error:
            raise PersistenceError("could not commit draft transition") from error

    def _write_session(self, connection: sqlite3.Connection, session: DraftSession) -> None:
        config_json = _config_to_json(session.config)
        existing_league = connection.execute(
            "SELECT config_json FROM leagues WHERE league_id = ?", (session.league_id.value,)
        ).fetchone()
        if existing_league is not None and existing_league[0] != config_json:
            raise PersistenceError("active league configuration is immutable")
        connection.execute(
            "INSERT INTO leagues(league_id, config_version, config_json, created_at) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(league_id) DO NOTHING",
            (session.league_id.value, session.config.config_version, config_json, _timestamp()),
        )
        connection.execute(
            "INSERT INTO drafts(draft_id, league_id, provider, provider_draft_id, user_team_id, "
            "user_slot, draft_order_json, dataset_version, feature_version, model_version, status, "
            "reconciliation_state, revision, issues_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(draft_id) DO UPDATE SET status = excluded.status, "
            "reconciliation_state = excluded.reconciliation_state, revision = excluded.revision, "
            "issues_json = excluded.issues_json",
            (
                session.draft_id.value,
                session.league_id.value,
                session.provider,
                session.provider_draft_id,
                session.user_team_id,
                session.user_slot,
                _json(session.draft_order),
                session.dataset_version,
                session.feature_version,
                session.model_version,
                session.status.value,
                session.reconciliation_state.value,
                session.revision,
                _json(session.issues),
            ),
        )
        # A recommendation is current only for the exact canonical revision it was calculated
        # from. Any committed draft mutation invalidates the prior current marker atomically.
        connection.execute(
            "UPDATE recommendation_snapshots SET is_current = 0 WHERE draft_id = ?",
            (session.draft_id.value,),
        )
        connection.execute("DELETE FROM picks WHERE draft_id = ?", (session.draft_id.value,))
        connection.executemany(
            "INSERT INTO picks(draft_id, overall_pick, team_id, internal_player_id, source, "
            "observed_at, "
            "event_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    session.draft_id.value,
                    pick.overall_pick,
                    pick.team_id,
                    pick.internal_player_id,
                    pick.source,
                    pick.observed_at.isoformat(),
                    pick.event_id,
                )
                for pick in session.accepted_picks
            ],
        )
        connection.execute(
            "DELETE FROM unresolved_observations WHERE draft_id = ?", (session.draft_id.value,)
        )
        connection.executemany(
            "INSERT INTO unresolved_observations(draft_id, observation_json) VALUES (?, ?)",
            [
                (session.draft_id.value, _unresolved_to_json(observation))
                for observation in session.unresolved_observations
            ],
        )

    def get_draft(self, draft_id: DraftId) -> DraftSession | None:
        row = self._connection.execute(
            "SELECT d.*, l.config_json FROM drafts d JOIN leagues l ON l.league_id = d.league_id "
            "WHERE d.draft_id = ?",
            (draft_id.value,),
        ).fetchone()
        return self._load_session(row) if row is not None else None

    def find_draft_by_provider(self, provider: str, provider_draft_id: str) -> DraftSession | None:
        row = self._connection.execute(
            "SELECT d.*, l.config_json FROM drafts d JOIN leagues l ON l.league_id = d.league_id "
            "WHERE d.provider = ? AND d.provider_draft_id = ?",
            (provider, provider_draft_id),
        ).fetchone()
        return self._load_session(row) if row is not None else None

    def _load_session(self, row: sqlite3.Row) -> DraftSession:
        picks = self._connection.execute(
            "SELECT overall_pick, team_id, internal_player_id, source, observed_at, event_id "
            "FROM picks WHERE draft_id = ? ORDER BY overall_pick",
            (row["draft_id"],),
        ).fetchall()
        unresolved = self._connection.execute(
            "SELECT observation_json FROM unresolved_observations WHERE draft_id = ? "
            "ORDER BY observation_id",
            (row["draft_id"],),
        ).fetchall()
        return DraftSession(
            draft_id=DraftId(row["draft_id"]),
            league_id=LeagueId(row["league_id"]),
            provider=row["provider"],
            provider_draft_id=row["provider_draft_id"],
            config=_config_from_json(row["config_json"]),
            user_team_id=row["user_team_id"],
            user_slot=row["user_slot"],
            draft_order=tuple(json.loads(row["draft_order_json"])),
            dataset_version=row["dataset_version"],
            feature_version=row["feature_version"],
            model_version=row["model_version"],
            status=DraftStatus(row["status"]),
            reconciliation_state=ReconciliationState(row["reconciliation_state"]),
            revision=row["revision"],
            accepted_picks=tuple(
                DraftPick(
                    overall_pick=pick["overall_pick"],
                    team_id=pick["team_id"],
                    internal_player_id=pick["internal_player_id"],
                    source=pick["source"],
                    observed_at=datetime.fromisoformat(pick["observed_at"]),
                    event_id=pick["event_id"],
                )
                for pick in picks
            ),
            unresolved_observations=tuple(_unresolved_from_json(item[0]) for item in unresolved),
            issues=tuple(json.loads(row["issues_json"])),
        )

    def save_event_outcome(
        self,
        draft_id: DraftId,
        event_id: str,
        fingerprint: str,
        outcome: str,
        resulting_revision: int,
    ) -> None:
        try:
            with self._transaction() as connection:
                connection.execute(
                    "INSERT INTO event_outcomes(draft_id, event_id, fingerprint, outcome, "
                    "resulting_revision) VALUES (?, ?, ?, ?, ?)",
                    (draft_id.value, event_id, fingerprint, outcome, resulting_revision),
                )
        except sqlite3.IntegrityError as error:
            raise PersistenceError("event outcome already exists") from error

    def get_event_outcome(self, draft_id: DraftId, event_id: str) -> tuple[str, str, int] | None:
        row = self._connection.execute(
            "SELECT fingerprint, outcome, resulting_revision FROM event_outcomes "
            "WHERE draft_id = ? AND event_id = ?",
            (draft_id.value, event_id),
        ).fetchone()
        return (row["fingerprint"], row["outcome"], row["resulting_revision"]) if row else None

    def set_metadata(self, key: str, value: str) -> None:
        if not key or not value:
            raise PersistenceError("metadata keys and values must be non-empty")
        try:
            with self._transaction() as connection:
                connection.execute(
                    "INSERT INTO metadata(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
        except sqlite3.DatabaseError as error:
            raise PersistenceError("could not persist metadata") from error

    def get_metadata(self, key: str) -> str | None:
        row = self._connection.execute(
            "SELECT value FROM metadata WHERE key = ?", (key,)
        ).fetchone()
        return str(row["value"]) if row is not None else None

    def save_reconciliation_record(
        self,
        draft_id: DraftId,
        source: str,
        observed_at: datetime,
        declared_complete: bool,
        differences: Mapping[str, object],
        outcome: str,
    ) -> None:
        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO reconciliation_records(draft_id, source, observed_at, "
                "declared_complete, "
                "differences_json, outcome) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    draft_id.value,
                    source,
                    observed_at.isoformat(),
                    int(declared_complete),
                    _json(differences),
                    outcome,
                ),
            )

    def commit_reconciliation(
        self,
        session: DraftSession,
        source: str,
        observed_at: datetime,
        declared_complete: bool,
        differences: Mapping[str, object],
        outcome: str,
    ) -> None:
        try:
            with self._transaction() as connection:
                self._write_session(connection, session)
                connection.execute(
                    "INSERT INTO reconciliation_records(draft_id, source, observed_at, "
                    "declared_complete, differences_json, outcome) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session.draft_id.value,
                        source,
                        observed_at.isoformat(),
                        int(declared_complete),
                        _json(differences),
                        outcome,
                    ),
                )
        except sqlite3.DatabaseError as error:
            raise PersistenceError("could not atomically reconcile canonical state") from error

    def save_recommendation(self, snapshot: RecommendationSnapshot) -> None:
        try:
            with self._transaction() as connection:
                current = self.get_draft(snapshot.draft_id)
                if current is None or current.status in {
                    DraftStatus.BLOCKED,
                    DraftStatus.RECONCILING,
                }:
                    raise PersistenceError(
                        "blocked or reconciling drafts cannot publish recommendations"
                    )
                if current.revision != snapshot.canonical_revision:
                    raise PersistenceError("recommendation snapshot is stale")
                connection.execute(
                    "UPDATE recommendation_snapshots SET is_current = 0 WHERE draft_id = ?",
                    (snapshot.draft_id.value,),
                )
                connection.execute(
                    "INSERT INTO recommendation_snapshots(snapshot_id, draft_id, "
                    "canonical_revision, "
                    "is_current, snapshot_json, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        snapshot.snapshot_id,
                        snapshot.draft_id.value,
                        snapshot.canonical_revision,
                        int(snapshot.is_current),
                        _snapshot_to_json(snapshot),
                        snapshot.generated_at.isoformat(),
                    ),
                )
        except sqlite3.DatabaseError as error:
            raise PersistenceError("could not persist recommendation snapshot") from error

    def latest_recommendation(self, draft_id: DraftId) -> RecommendationSnapshot | None:
        row = self._connection.execute(
            "SELECT snapshot_json FROM recommendation_snapshots WHERE draft_id = ? "
            "AND is_current = 1 "
            "ORDER BY canonical_revision DESC, created_at DESC LIMIT 1",
            (draft_id.value,),
        ).fetchone()
        return _snapshot_from_json(row[0]) if row is not None else None
