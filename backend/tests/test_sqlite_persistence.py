from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    DraftPick,
    DraftSession,
    LeagueConfig,
    LeagueId,
    Player,
    RosterSlot,
    apply_pick,
)
from nfl_fantasy_assistant.persistence import PersistenceError, SqliteDraftRepository


def session() -> DraftSession:
    return DraftSession(
        draft_id=DraftId("draft-1"),
        league_id=LeagueId("league-1"),
        provider="espn",
        provider_draft_id="provider-draft-1",
        config=LeagueConfig(
            "league-v1",
            2,
            "snake",
            (RosterSlot("RB", frozenset({"RB"})),),
            {"receptions": 1.0},
        ),
        user_team_id="team-1",
        user_slot=1,
        draft_order=("team-1", "team-2", "team-2", "team-1"),
        dataset_version="dataset-1",
        feature_version="feature-1",
        model_version="model-1",
    )


def player(identifier: str) -> Player:
    return Player(identifier, {"espn": identifier}, f"Player {identifier}", "RB")


def pick(number: int, team: str, identifier: str) -> DraftPick:
    return DraftPick(number, team, identifier, "espn", datetime.now(UTC), f"event-{number}")


def test_migration_create_load_and_restart(tmp_path: Path) -> None:
    database = tmp_path / "state" / "drafts.sqlite3"
    repository = SqliteDraftRepository(database)
    repository.save_player(player("one"))
    original = apply_pick(session(), pick(1, "team-1", "one"))
    repository.save_draft(original)
    repository.close()

    restarted = SqliteDraftRepository(database)
    loaded = restarted.get_draft(DraftId("draft-1"))
    assert loaded == original
    assert restarted.find_player_by_external_id("espn", "one") == player("one")
    assert [
        row[0] for row in restarted._connection.execute("SELECT version FROM schema_migrations")
    ] == [1, 2, 3]


def test_transition_rollback_and_database_constraints_preserve_previous_state(
    tmp_path: Path,
) -> None:
    repository = SqliteDraftRepository(tmp_path / "drafts.sqlite3")
    repository.save_player(player("one"))
    original = apply_pick(session(), pick(1, "team-1", "one"))
    repository.save_draft(original)
    invalid = apply_pick(original, pick(2, "team-2", "missing"))
    with pytest.raises(PersistenceError, match="conflicts"):
        repository.commit_transition(invalid, "event-2", "fingerprint", "accepted")
    assert repository.get_draft(DraftId("draft-1")) == original
    with pytest.raises(PersistenceError, match="mapped differently"):
        repository.save_player(Player("other", {"espn": "one"}, "Other", "RB"))


def test_event_outcomes_are_unique_and_save_with_state_atomically(tmp_path: Path) -> None:
    repository = SqliteDraftRepository(tmp_path / "drafts.sqlite3")
    repository.save_player(player("one"))
    accepted = apply_pick(session(), pick(1, "team-1", "one"))
    repository.commit_transition(accepted, "event-1", "fingerprint", "accepted")
    assert repository.get_event_outcome(DraftId("draft-1"), "event-1") == (
        "fingerprint",
        "accepted",
        1,
    )
    with pytest.raises(PersistenceError, match="conflicts"):
        repository.commit_transition(accepted, "event-1", "fingerprint", "accepted")
    repository.set_metadata("dataset_version", "dataset-1")
    assert repository.get_metadata("dataset_version") == "dataset-1"


def test_migration_refuses_unknown_past_version(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    connection.execute("INSERT INTO schema_migrations VALUES (99, 'now')")
    connection.commit()
    connection.close()
    with pytest.raises(PersistenceError, match="unknown"):
        SqliteDraftRepository(path)
