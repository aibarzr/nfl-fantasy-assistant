from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nfl_fantasy_assistant.domain.draft import (
    AssetType,
    DomainError,
    DraftId,
    DraftPick,
    DraftSession,
    DraftStatus,
    LeagueConfig,
    LeagueId,
    Player,
    RosterSlot,
    apply_pick,
    derive_availability,
    derive_rosters,
)


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
            (
                RosterSlot("QB", frozenset({"QB"})),
                RosterSlot("RB", frozenset({"RB"})),
                RosterSlot("FLEX", frozenset({"RB", "WR", "TE"})),
                RosterSlot("BN", frozenset({"QB", "RB", "WR", "TE"}), is_bench=True),
            ),
            {"receptions": 1.0},
        ),
        user_team_id="team-1",
        user_slot=1,
        draft_order=("team-1", "team-2", "team-2", "team-1"),
        dataset_version="dataset-1",
        feature_version="feature-1",
        model_version="model-1",
    )


def pick(number: int, team: str, player: str) -> DraftPick:
    return DraftPick(number, team, player, "espn", datetime.now(UTC), f"event-{number}")


def test_valid_transition_preserves_config_and_derives_state() -> None:
    state = apply_pick(session(), pick(1, "team-1", "player-qb"))
    assert state.status is DraftStatus.ACTIVE
    assert state.revision == 1
    assert state.current_pick == 2
    assert derive_availability(("player-qb", "player-rb"), state.accepted_picks) == ("player-rb",)
    players = {
        "player-qb": Player("player-qb", {"espn": "1"}, "Name", "QB"),
    }
    roster = derive_rosters(state, players)[0]
    assert roster.assignments[0].slot_name == "QB"
    with pytest.raises(TypeError):
        state.config.scoring_rules["receptions"] = 2.0  # type: ignore[index]


def test_domain_rejects_duplicate_players_and_wrong_draft_order() -> None:
    state = apply_pick(session(), pick(1, "team-1", "player-a"))
    with pytest.raises(DomainError, match="drafted at most once"):
        apply_pick(state, pick(2, "team-2", "player-a"))
    with pytest.raises(DomainError, match="draft order"):
        apply_pick(session(), pick(2, "team-1", "player-b"))


def test_gap_requires_reconciliation_without_reordering_history() -> None:
    state = apply_pick(session(), pick(2, "team-2", "player-b"))
    assert state.status is DraftStatus.RECONCILING
    assert state.current_pick == 1
    assert state.accepted_picks[0].overall_pick == 2


def test_availability_and_roster_derivation_reject_corruption() -> None:
    with pytest.raises(DomainError, match="duplicate"):
        derive_availability(("player-a", "player-a"), ())
    state = apply_pick(session(), pick(1, "team-1", "missing"))
    with pytest.raises(DomainError, match="known internal players"):
        derive_rosters(state, {})


def test_team_defense_is_an_explicit_team_asset_and_can_fill_a_def_slot() -> None:
    config = LeagueConfig(
        "league-v1",
        2,
        "snake",
        (RosterSlot("DEF", frozenset({"DEF"})),),
        {},
    )
    state = DraftSession(
        DraftId("draft-def"),
        LeagueId("league-def"),
        "sleeper",
        "provider-def",
        config,
        "team-1",
        1,
        ("team-1", "team-2"),
        "dataset-1",
        "feature-1",
        "model-1",
    )
    updated = apply_pick(state, pick(1, "team-1", "defense-chi"))
    defense = Player("defense-chi", {"sleeper": "CHI"}, "Chicago", "DEF", "CHI")
    assert defense.asset_type is AssetType.TEAM_DEFENSE
    assert derive_rosters(updated, {"defense-chi": defense})[0].assignments[0].slot_name == "DEF"
    with pytest.raises(DomainError, match="NFL team"):
        Player("defense-missing", {"sleeper": "missing"}, "Missing", "DEF")
