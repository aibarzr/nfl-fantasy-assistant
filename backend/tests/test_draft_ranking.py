from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    DraftPick,
    DraftSession,
    DraftStatus,
    LeagueConfig,
    LeagueId,
    RosterSlot,
)
from nfl_fantasy_assistant.models.draft_ranking import (
    DraftRankInput,
    RankingError,
    rank_draft_candidates,
)
from nfl_fantasy_assistant.models.projection import PlayerProjection
from nfl_fantasy_assistant.models.replacement import ValueOverReplacement, value_over_replacement
from nfl_fantasy_assistant.models.valuation import PlayerValue


def session(pick_count: int = 0, status: DraftStatus = DraftStatus.ACTIVE) -> DraftSession:
    order = tuple(team for _ in range(12) for team in ("team-1", "team-2"))
    picks = tuple(
        DraftPick(index, order[index - 1], f"drafted-{index}", "fixture", datetime.now(UTC))
        for index in range(1, pick_count + 1)
    )
    return DraftSession(
        DraftId("draft"),
        LeagueId("league"),
        "espn",
        "provider-draft",
        LeagueConfig(
            "config",
            2,
            "snake",
            (
                RosterSlot("RB", frozenset({"RB"})),
                RosterSlot("FLEX", frozenset({"RB", "WR", "TE"})),
            ),
            {},
        ),
        "team-1",
        1,
        order,
        "dataset-v1",
        "feature-v1",
        "model-v1",
        status,
        accepted_picks=picks,
    )


def rank_input(
    identifier: str, position: str, vor: float, market: float, uncertainty: float = 0.1
) -> DraftRankInput:
    value = PlayerValue(
        identifier,
        position,
        0.5,
        0.8,
        uncertainty,
        {"market_prior": market},
        (),
        "value-v1",
        "norm-v1",
    )
    replacement = ValueOverReplacement(identifier, position, 0.5, 0.2, vor, {})
    projection = PlayerProjection(
        identifier, position, 15, 10, 22, 0.8, {}, (), "projection-v1", "semantic-v1"
    )
    return DraftRankInput(value, replacement, projection)


def test_ranking_returns_explainable_versioned_top_n_with_canonical_filtering() -> None:
    inputs = (
        rank_input("rb-high", "RB", 0.6, 0.4),
        rank_input("wr-market", "WR", 0.4, 1.0),
        rank_input("te-low", "TE", 0.1, 0.2),
    )
    result = rank_draft_candidates(session(), inputs, {}, top_n=2)
    assert len(result) == 2
    assert result[0].candidate.rank == 1
    assert set(result[0].candidate.components) == {
        "vor",
        "urgency",
        "scarcity",
        "market",
        "roster",
        "risk_upside",
    }
    assert result[0].ranking_version == "draft-ranking-v1"
    assert result[0].feature_version == "feature-v1"
    assert result == rank_draft_candidates(session(), inputs, {}, top_n=2)


@pytest.mark.parametrize(("pick_count", "stage"), ((0, "early"), (8, "middle"), (18, "late")))
def test_ranking_uses_stage_profiles_and_roster_pressure(pick_count: int, stage: str) -> None:
    active = session(pick_count)
    positions = {pick.internal_player_id: "RB" for pick in active.accepted_picks}
    result = rank_draft_candidates(active, (rank_input("rb", "RB", 0.5, 0.5),), positions)
    assert result[0].stage == stage
    assert result[0].candidate.components["roster"] >= 0


def test_ranking_rejects_blocked_or_drafted_availability() -> None:
    with pytest.raises(RankingError, match="cannot rank"):
        rank_draft_candidates(session(status=DraftStatus.BLOCKED), (), {})
    active = session(1)
    with pytest.raises(RankingError, match="drafted players"):
        rank_draft_candidates(
            active,
            (rank_input("drafted-1", "RB", 0.5, 0.5),),
            {"drafted-1": "RB"},
        )


def test_k_and_def_have_replacement_and_explainable_ranking_coverage() -> None:
    active = DraftSession(
        DraftId("k-def-draft"),
        LeagueId("k-def-league"),
        "fixture",
        "k-def-provider-draft",
        LeagueConfig(
            "k-def-config",
            2,
            "snake",
            (
                RosterSlot("K", frozenset({"K"})),
                RosterSlot("DEF", frozenset({"DEF"})),
                RosterSlot("BN", frozenset({"K", "DEF"}), is_bench=True),
            ),
            {"field_goals_made": 3, "defensive_sacks": 1},
        ),
        "team-1",
        1,
        ("team-1", "team-2", "team-2", "team-1"),
        "k-def-fixture-v1",
        "feature-v2",
        "projection-v2",
        DraftStatus.ACTIVE,
    )
    values = (
        rank_input("kicker-1", "K", 0, 0.5).player_value,
        rank_input("defense-1", "DEF", 0, 0.5).player_value,
    )
    vors = {
        item.internal_player_id: item for item in value_over_replacement(active.config, values, {})
    }
    inputs = tuple(
        DraftRankInput(
            value,
            vors[value.internal_player_id],
            rank_input(value.internal_player_id, value.position, 0, 0.5).projection,
        )
        for value in values
    )
    ranked = rank_draft_candidates(active, inputs, {}, top_n=2)
    assert {item.candidate.internal_player_id for item in ranked} == {"kicker-1", "defense-1"}
    assert all("vor" in item.candidate.components for item in ranked)
