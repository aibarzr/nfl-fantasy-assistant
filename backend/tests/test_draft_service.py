from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from nfl_fantasy_assistant.application.drafts import (
    ApplicationError,
    DraftEvent,
    DraftService,
    DraftSnapshot,
    ObservedPick,
)
from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    DraftStatus,
    LeagueConfig,
    Player,
    PlayerReference,
    RecommendationCandidate,
    RecommendationSnapshot,
    RosterSlot,
)
from nfl_fantasy_assistant.persistence import PersistenceError, SqliteDraftRepository


def config() -> LeagueConfig:
    return LeagueConfig(
        "config-v1",
        8,
        "snake",
        (
            RosterSlot("QB", frozenset({"QB"})),
            RosterSlot("RB", frozenset({"RB"})),
            RosterSlot("BN", frozenset({"QB", "RB", "WR", "TE"}), is_bench=True),
        ),
        {"receptions": 1.0},
    )


def order() -> tuple[str, ...]:
    first = tuple(f"team-{number}" for number in range(1, 9))
    return (*first, *reversed(first))


def observed(number: int, player: str, team: str | None = None) -> ObservedPick:
    return ObservedPick(
        number,
        team or order()[number - 1],
        PlayerReference("espn", player),
    )


def event(event_id: str, number: int, player: str, team: str | None = None) -> DraftEvent:
    return DraftEvent(event_id, datetime.now(UTC), "espn", "espn", observed(number, player, team))


def initialized(tmp_path: Path) -> tuple[SqliteDraftRepository, DraftService, DraftId]:
    repository = SqliteDraftRepository(tmp_path / "drafts.sqlite3")
    for player_id, position in (("one", "QB"), ("two", "RB"), ("three", "RB")):
        repository.save_player(
            Player(f"player-{player_id}", {"espn": player_id}, player_id, position)
        )
    service = DraftService(repository)
    league_id = service.register_league("espn", "league-external", config())
    state = service.initialize_or_resume(
        league_id,
        "espn",
        "draft-external",
        config(),
        "team-1",
        1,
        order(),
        "dataset-v1",
        "feature-v1",
        "model-v1",
    )
    return repository, service, state.draft_id


def test_initialize_resumes_stable_internal_draft_and_rejects_non_mvp_size(tmp_path: Path) -> None:
    _, service, draft_id = initialized(tmp_path)
    league_id = service.register_league("espn", "league-external", config())
    resumed = service.initialize_or_resume(
        league_id,
        "espn",
        "draft-external",
        config(),
        "team-1",
        1,
        order(),
        "dataset-v1",
        "feature-v1",
        "model-v1",
    )
    assert resumed.draft_id == draft_id
    unsupported = LeagueConfig("v", 10, "snake", config().roster_slots, {})
    with pytest.raises(ApplicationError, match="8-team"):
        service.initialize_or_resume(
            league_id,
            "espn",
            "other",
            unsupported,
            "team-1",
            1,
            order(),
            "dataset-v1",
            "feature-v1",
            "model-v1",
        )


def test_events_are_idempotent_conflict_safe_and_leave_unknown_players_unavailable(
    tmp_path: Path,
) -> None:
    repository, service, draft_id = initialized(tmp_path)
    accepted = service.ingest_event(draft_id, event("event-1", 1, "one"))
    assert accepted.outcome == "accepted"
    assert service.ingest_event(draft_id, event("event-1", 1, "one")).replayed is True
    with pytest.raises(ApplicationError, match="already used"):
        service.ingest_event(draft_id, event("event-1", 1, "two"))
    unknown = service.ingest_event(draft_id, event("event-2", 2, "unknown"))
    assert unknown.outcome == "accepted_needs_reconciliation"
    assert service.availability(draft_id, ("player-one", "player-two")) == ("player-two",)
    state = repository.get_draft(draft_id)
    assert state is not None
    assert state.unresolved_observations[0].reference.external_id == "unknown"


def test_gap_and_snapshot_conflict_preserve_history_and_block_draft(tmp_path: Path) -> None:
    repository, service, draft_id = initialized(tmp_path)
    gap = service.ingest_event(draft_id, event("event-2", 2, "two"))
    assert gap.outcome == "accepted_needs_reconciliation"
    result = service.reconcile(
        draft_id,
        DraftSnapshot("espn", datetime.now(UTC), True, (observed(2, "three"),)),
    )
    assert result.outcome == "conflict"
    state = repository.get_draft(draft_id)
    assert state is not None and state.status is DraftStatus.BLOCKED
    assert state.accepted_picks[0].internal_player_id == "player-two"


def test_snapshot_repairs_only_missing_picks_and_rosters_are_derived(tmp_path: Path) -> None:
    _, service, draft_id = initialized(tmp_path)
    service.ingest_event(draft_id, event("event-1", 1, "one"))
    result = service.reconcile(
        draft_id,
        DraftSnapshot("espn", datetime.now(UTC), False, (observed(1, "one"), observed(2, "two"))),
    )
    assert result.outcome == "reconciled"
    assert [roster.team_id for roster in service.rosters(draft_id)] == list(dict.fromkeys(order()))


def test_recommendation_provenance_survives_restart_and_rejects_stale_or_blocked_state(
    tmp_path: Path,
) -> None:
    repository, service, draft_id = initialized(tmp_path)
    service.ingest_event(draft_id, event("event-1", 1, "one"))
    state = repository.get_draft(draft_id)
    assert state is not None
    snapshot = RecommendationSnapshot(
        "recommendation-1",
        draft_id,
        state.revision,
        datetime.now(UTC),
        ("player-three", "player-two"),
        (
            RecommendationCandidate(
                "player-one", 1, 12.5, 0.8, {"value": 1.0}, ("fixture",), "Fixture candidate."
            ),
        ),
        state.config.config_version,
        state.dataset_version,
        state.feature_version,
        state.model_version,
        {"prepared_pool": "2026-08-01T00:00:00Z"},
    )
    repository.save_recommendation(snapshot)
    repository.close()
    restarted = SqliteDraftRepository(tmp_path / "drafts.sqlite3")
    assert restarted.latest_recommendation(draft_id) == snapshot
    stale = RecommendationSnapshot(
        "recommendation-stale",
        draft_id,
        state.revision + 1,
        datetime.now(UTC),
        snapshot.available_player_ids,
        snapshot.candidates,
        snapshot.config_version,
        snapshot.dataset_version,
        snapshot.feature_version,
        snapshot.model_version,
        snapshot.source_updated_at,
    )
    with pytest.raises(PersistenceError, match="stale"):
        restarted.save_recommendation(stale)
    assert restarted.latest_recommendation(draft_id) == snapshot
    service_after_restart = DraftService(restarted)
    service_after_restart.reconcile(
        draft_id,
        DraftSnapshot("espn", datetime.now(UTC), True, (observed(1, "two"),)),
    )
    with pytest.raises(PersistenceError, match="blocked"):
        restarted.save_recommendation(snapshot)
