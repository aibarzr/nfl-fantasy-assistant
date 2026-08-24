"""Time-safe historical participation and durability evidence.

This module deliberately models participation evidence, not a medical diagnosis.  Its callers must
provide a complete player-team-week eligibility calendar: a player-stat row alone can prove a
participation observation but cannot manufacture omitted eligible weeks, byes, or injury causes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from .errors import DataValidationError


class ParticipationState(StrEnum):
    """Observed relationship to an eligible team game; never an injury diagnosis."""

    PARTICIPATED = "participated"
    DID_NOT_PARTICIPATE = "did_not_participate"
    UNKNOWN = "unknown"
    BYE = "bye"


@dataclass(frozen=True, slots=True)
class ScheduledTeamGame:
    """One regular-season team game after source-specific schedule translation."""

    season: int
    week: int
    home_team: str
    away_team: str
    lineage_manifest_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeeklyRosterMember:
    """Exact roster membership used to define an eligible player/team/week."""

    source_player_id: str
    nfl_team: str
    season: int
    week: int
    lineage_manifest_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlayerWeekUsageEvidence:
    """Exact participation evidence after source IDs have been reconciled in the data layer."""

    source_player_id: str
    nfl_team: str
    season: int
    week: int
    snap_count: int | None
    has_stat_line: bool
    lineage_manifest_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.snap_count is not None and self.snap_count < 0:
            raise DataValidationError("snap count cannot be negative")


@dataclass(frozen=True, slots=True)
class PlayerWeekParticipation:
    """One exact player/team/season/week calendar observation with retained lineage."""

    source_player_id: str
    nfl_team: str
    season: int
    week: int
    state: ParticipationState
    lineage_manifest_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            not self.source_player_id
            or not self.nfl_team
            or self.season < 2000
            or not 1 <= self.week <= 18
            or not self.lineage_manifest_ids
        ):
            raise DataValidationError("participation evidence requires exact identity and lineage")


@dataclass(frozen=True, slots=True)
class DurabilityFeature:
    """Rates at a player-week cutoff; null if their required evidence is incomplete."""

    source_player_id: str
    season: int
    week: int
    observation_cutoff: tuple[int, int]
    durability_rate_4: float | None
    durability_rate_8: float | None
    prior_season_participation_rate: float | None
    multi_season_durability: float | None
    lineage_manifest_ids: tuple[str, ...]


def build_participation_calendar(
    scheduled_games: Iterable[ScheduledTeamGame],
    weekly_rosters: Iterable[WeeklyRosterMember],
    usage_evidence: Iterable[PlayerWeekUsageEvidence],
    *,
    schedule_complete: bool,
) -> tuple[PlayerWeekParticipation, ...]:
    """Derive a calendar only from exact, source-translated schedule/roster/usage facts.

    The caller proves schedule completeness after retrieving all regular-season source rows. A
    roster member on a team absent from that complete week's schedule is a bye; without that proof
    it would be unknown, so this function rejects the input rather than guessing.
    """
    if not schedule_complete:
        raise DataValidationError("durability calendar requires a complete schedule declaration")
    games = tuple(scheduled_games)
    roster_rows = tuple(weekly_rosters)
    usage_rows = tuple(usage_evidence)
    scheduled_teams: set[tuple[int, int, str]] = set()
    game_lineage: dict[tuple[int, int], set[str]] = defaultdict(set)
    for game in games:
        for team in (game.home_team, game.away_team):
            scheduled_team_key = (game.season, game.week, team)
            if scheduled_team_key in scheduled_teams:
                raise DataValidationError("schedule has duplicate team game evidence")
            scheduled_teams.add(scheduled_team_key)
        game_lineage[(game.season, game.week)].update(game.lineage_manifest_ids)
    usage_by_key: dict[tuple[str, str, int, int], PlayerWeekUsageEvidence] = {}
    for usage_row in usage_rows:
        usage_key = (
            usage_row.source_player_id,
            usage_row.nfl_team,
            usage_row.season,
            usage_row.week,
        )
        if usage_key in usage_by_key:
            raise DataValidationError("duplicate exact player-week usage evidence")
        usage_by_key[usage_key] = usage_row
    result: list[PlayerWeekParticipation] = []
    roster_keys: set[tuple[str, int, int]] = set()
    for member in roster_rows:
        calendar_key = (member.source_player_id, member.season, member.week)
        if calendar_key in roster_keys:
            raise DataValidationError("player has ambiguous weekly roster membership")
        roster_keys.add(calendar_key)
        player_usage = usage_by_key.get(
            (member.source_player_id, member.nfl_team, member.season, member.week)
        )
        if (member.season, member.week, member.nfl_team) not in scheduled_teams:
            state = ParticipationState.BYE
        elif player_usage is None:
            state = ParticipationState.UNKNOWN
        elif player_usage.snap_count is not None:
            state = (
                ParticipationState.PARTICIPATED
                if player_usage.snap_count > 0
                else ParticipationState.DID_NOT_PARTICIPATE
            )
        elif player_usage.has_stat_line:
            state = ParticipationState.PARTICIPATED
        else:
            state = ParticipationState.UNKNOWN
        lineage = set(member.lineage_manifest_ids)
        lineage.update(game_lineage.get((member.season, member.week), set()))
        if player_usage is not None:
            lineage.update(player_usage.lineage_manifest_ids)
        result.append(
            PlayerWeekParticipation(
                member.source_player_id,
                member.nfl_team,
                member.season,
                member.week,
                state,
                tuple(sorted(lineage)),
            )
        )
    return tuple(sorted(result, key=lambda item: (item.source_player_id, item.season, item.week)))


def _complete_rate(window: list[PlayerWeekParticipation]) -> float | None:
    """Return a rate only when every eligible week has a supported observation."""
    if not window or any(item.state is ParticipationState.UNKNOWN for item in window):
        return None
    return sum(item.state is ParticipationState.PARTICIPATED for item in window) / len(window)


def _prior_season_rate(
    history: list[PlayerWeekParticipation], season: int
) -> tuple[float | None, tuple[str, ...]]:
    prior = [item for item in history if item.season < season]
    if not prior:
        return None, ()
    seasons = sorted({item.season for item in prior}, reverse=True)
    rates: list[float] = []
    lineage: set[str] = set()
    # Newest-to-oldest weights preserve recency while never substituting incomplete season data.
    weights = (0.55, 0.25, 0.13, 0.07)
    for prior_season in seasons[: len(weights)]:
        values = [item for item in prior if item.season == prior_season]
        rate = _complete_rate(values)
        if rate is None:
            return None, ()
        rates.append(rate)
        lineage.update(lineage_id for item in values for lineage_id in item.lineage_manifest_ids)
    active_weights = weights[: len(rates)]
    denominator = sum(active_weights)
    return (
        sum(rate * weight for rate, weight in zip(rates, active_weights, strict=True))
        / denominator,
        tuple(sorted(lineage)),
    )


def build_durability_features(
    observations: Iterable[PlayerWeekParticipation],
) -> tuple[DurabilityFeature, ...]:
    """Create pre-cutoff durability features from a complete eligible-week calendar.

    Byes are not eligible weeks and therefore never lower a participation rate.  Every other
    expected player-team-week must be represented explicitly; missing source evidence is
    ``UNKNOWN`` and makes the affected window unavailable rather than silently shortening it.
    """
    ordered = sorted(
        observations,
        key=lambda item: (item.source_player_id, item.season, item.week, item.nfl_team),
    )
    seen: set[tuple[str, int, int]] = set()
    history_by_player: dict[str, list[PlayerWeekParticipation]] = defaultdict(list)
    result: list[DurabilityFeature] = []
    for observation in ordered:
        key = (observation.source_player_id, observation.season, observation.week)
        if key in seen:
            raise DataValidationError(f"duplicate participation calendar key: {key}")
        seen.add(key)
        history = history_by_player[observation.source_player_id]
        eligible_history = [item for item in history if item.state is not ParticipationState.BYE]
        recent_4 = eligible_history[-4:]
        recent_8 = eligible_history[-8:]
        prior_rate, prior_lineage = _prior_season_rate(eligible_history, observation.season)
        current_lineage = tuple(
            sorted(
                {
                    lineage_id
                    for item in (*recent_8, *eligible_history)
                    for lineage_id in item.lineage_manifest_ids
                }
                | set(prior_lineage)
            )
        )
        result.append(
            DurabilityFeature(
                observation.source_player_id,
                observation.season,
                observation.week,
                (observation.season, observation.week - 1),
                _complete_rate(recent_4) if len(recent_4) == 4 else None,
                _complete_rate(recent_8) if len(recent_8) == 8 else None,
                _complete_rate(
                    [item for item in eligible_history if item.season == observation.season - 1]
                ),
                prior_rate,
                current_lineage,
            )
        )
        history.append(observation)
    return tuple(result)
