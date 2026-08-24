from __future__ import annotations

import pytest

from nfl_fantasy_assistant.data.curation import curate_weeks
from nfl_fantasy_assistant.data.durability import (
    ParticipationState,
    PlayerWeekParticipation,
    PlayerWeekUsageEvidence,
    ScheduledTeamGame,
    WeeklyRosterMember,
    build_durability_features,
    build_participation_calendar,
)
from nfl_fantasy_assistant.data.errors import DataValidationError
from nfl_fantasy_assistant.data.features import build_semantic_features


def observation(
    week: int,
    state: ParticipationState,
    *,
    season: int = 2025,
    team: str = "AAA",
) -> PlayerWeekParticipation:
    return PlayerWeekParticipation("player-1", team, season, week, state, ("source-1",))


def test_durability_excludes_byes_and_refuses_to_shorten_unknown_windows() -> None:
    features = build_durability_features(
        [
            observation(1, ParticipationState.PARTICIPATED),
            observation(2, ParticipationState.BYE),
            observation(3, ParticipationState.PARTICIPATED),
            observation(4, ParticipationState.DID_NOT_PARTICIPATE),
            observation(5, ParticipationState.PARTICIPATED),
            observation(6, ParticipationState.UNKNOWN),
            observation(7, ParticipationState.PARTICIPATED),
        ]
    )

    assert features[5].durability_rate_4 == pytest.approx(0.75)
    # At week seven the four prior eligible weeks include unknown week six, so the feature stays
    # unavailable instead of silently using an older short window.
    assert features[6].durability_rate_4 is None
    assert features[6].durability_rate_8 is None


def test_durability_prior_season_recency_is_time_safe_and_requires_complete_evidence() -> None:
    features = build_durability_features(
        [
            observation(1, ParticipationState.PARTICIPATED, season=2024),
            observation(2, ParticipationState.DID_NOT_PARTICIPATE, season=2024),
            observation(1, ParticipationState.PARTICIPATED, season=2025),
        ]
    )

    assert features[-1].prior_season_participation_rate == pytest.approx(0.5)
    assert features[-1].multi_season_durability == pytest.approx(0.5)


def test_durability_requires_one_exact_calendar_row_per_player_week() -> None:
    with pytest.raises(DataValidationError, match="duplicate participation calendar key"):
        build_durability_features(
            [
                observation(1, ParticipationState.PARTICIPATED),
                observation(1, ParticipationState.DID_NOT_PARTICIPATE, team="BBB"),
            ]
        )


def test_calendar_distinguishes_bye_participation_nonparticipation_and_unknown() -> None:
    calendar = build_participation_calendar(
        (
            ScheduledTeamGame(2025, 1, "AAA", "BBB", ("schedule-1",)),
            ScheduledTeamGame(2025, 2, "BBB", "CCC", ("schedule-1",)),
            ScheduledTeamGame(2025, 3, "AAA", "CCC", ("schedule-1",)),
            ScheduledTeamGame(2025, 4, "AAA", "BBB", ("schedule-1",)),
        ),
        tuple(
            WeeklyRosterMember("player-1", "AAA", 2025, week, ("roster-1",)) for week in range(1, 5)
        ),
        (
            PlayerWeekUsageEvidence("player-1", "AAA", 2025, 1, 12, False, ("snaps-1",)),
            PlayerWeekUsageEvidence("player-1", "AAA", 2025, 3, 0, False, ("snaps-1",)),
        ),
        schedule_complete=True,
    )

    assert [row.state for row in calendar] == [
        ParticipationState.PARTICIPATED,
        ParticipationState.BYE,
        ParticipationState.DID_NOT_PARTICIPATE,
        ParticipationState.UNKNOWN,
    ]
    assert set(calendar[0].lineage_manifest_ids) == {"schedule-1", "roster-1", "snaps-1"}


def test_calendar_rejects_incomplete_schedule_and_ambiguous_roster_membership() -> None:
    roster = WeeklyRosterMember("player-1", "AAA", 2025, 1, ("roster-1",))
    with pytest.raises(DataValidationError, match="complete schedule"):
        build_participation_calendar((), (roster,), (), schedule_complete=False)
    with pytest.raises(DataValidationError, match="ambiguous weekly roster"):
        build_participation_calendar(
            (ScheduledTeamGame(2025, 1, "AAA", "BBB", ("schedule-1",)),),
            (roster, WeeklyRosterMember("player-1", "BBB", 2025, 1, ("roster-1",))),
            (),
            schedule_complete=True,
        )


def test_semantic_features_retain_durability_separately_from_availability() -> None:
    weeks = curate_weeks(
        [
            {
                "player_id": "player-1",
                "season": 2025,
                "week": week,
                "position": "RB",
                "active": None,
                "source_updated_at": "2025-01-01T00:00:00+00:00",
            }
            for week in range(1, 6)
        ],
        "source-1",
    )
    durability = build_durability_features(
        [observation(week, ParticipationState.PARTICIPATED) for week in range(1, 6)]
    )

    feature = build_semantic_features(weeks, durability)[-1]
    assert feature.availability_rate_4 is None
    assert feature.durability_rate_4 == pytest.approx(1.0)
