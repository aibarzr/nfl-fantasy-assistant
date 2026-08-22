"""Deterministic nflverse play-by-play transforms for kicker and team-defense assets."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .errors import DataValidationError


@dataclass(frozen=True, slots=True)
class KDefSourceRows:
    """Source-shaped rows ready for the existing curated player/week boundary."""

    players: tuple[Mapping[str, object], ...]
    weeks: tuple[Mapping[str, object], ...]


def _text(row: Mapping[str, object], field: str) -> str | None:
    value = row.get(field)
    return None if value is None or str(value).strip() == "" else str(value).strip()


def _as_number(value: object, field: str) -> float:
    if value is None or value == "":
        return 0.0
    try:
        if isinstance(value, str | int | float):
            return float(value)
        raise TypeError
    except (TypeError, ValueError) as error:
        raise DataValidationError(f"PBP field {field} must be numeric") from error


def _number(row: Mapping[str, object], field: str) -> float:
    return _as_number(row.get(field), field)


def _as_int(value: object, field: str) -> int:
    number = _as_number(value, field)
    if not number.is_integer():
        raise DataValidationError(f"PBP field {field} must be an integer")
    return int(number)


def _flag(row: Mapping[str, object], field: str) -> bool:
    return _number(row, field) > 0


def _required_text(row: Mapping[str, object], field: str) -> str:
    value = _text(row, field)
    if value is None:
        raise DataValidationError(f"K/DEF PBP transform requires {field}")
    return value


def _week_key(row: Mapping[str, object], team: str) -> tuple[int, int, str]:
    try:
        season = _as_int(row["season"], "season")
        week = _as_int(row["week"], "week")
    except (KeyError, TypeError, ValueError) as error:
        raise DataValidationError("K/DEF PBP transform requires integer season and week") from error
    return season, week, team


def transform_pbp_k_def(
    rows: Iterable[Mapping[str, object]], *, source_updated_at: str
) -> KDefSourceRows:
    """Aggregate approved PBP fields without names as identities or incomplete score guesses.

    K uses the authoritative kicker player ID on field-goal and extra-point attempts. DEF uses a
    stable team asset ID and final game scores plus defensive-play facts. Only pass/rush play yards
    contribute to defensive yards allowed, matching the offensive-yard interpretation rather than
    mixing return yards into the metric.
    """

    if not source_updated_at:
        raise DataValidationError("K/DEF transform requires source update timestamp")
    kickers: dict[tuple[int, int, str], dict[str, object]] = {}
    defenses: dict[tuple[int, int, str], dict[str, float]] = defaultdict(
        lambda: {
            "defensive_sacks": 0.0,
            "defensive_interceptions": 0.0,
            "defensive_fumble_recoveries": 0.0,
            "defensive_touchdowns": 0.0,
            "yards_allowed": 0.0,
        }
    )
    defense_games: dict[tuple[int, int, str], set[str]] = defaultdict(set)
    game_scores: dict[str, tuple[str, str, float, float]] = {}

    for row in rows:
        season_type = _text(row, "season_type")
        if season_type is not None and season_type != "REG":
            continue
        game_id = _required_text(row, "game_id")
        home_team = _required_text(row, "home_team").upper()
        away_team = _required_text(row, "away_team").upper()
        home_score = _number(row, "total_home_score")
        away_score = _number(row, "total_away_score")
        prior = game_scores.get(game_id)
        if prior is not None and prior[:2] != (home_team, away_team):
            raise DataValidationError("PBP game has inconsistent home/away teams")
        game_scores[game_id] = (
            home_team,
            away_team,
            max(home_score, prior[2] if prior else 0.0),
            max(away_score, prior[3] if prior else 0.0),
        )

        defteam = _text(row, "defteam")
        if defteam is not None:
            defense_team = defteam.upper()
            defense_key = _week_key(row, defense_team)
            defense_games[defense_key].add(game_id)
            stats = defenses[defense_key]
            stats["defensive_sacks"] += float(_flag(row, "sack"))
            stats["defensive_interceptions"] += float(_flag(row, "interception"))
            stats["defensive_fumble_recoveries"] += float(_flag(row, "fumble_lost"))
            stats["defensive_touchdowns"] += float(
                _flag(row, "return_touchdown") and _text(row, "td_team") == defense_team
            )
            if _text(row, "play_type") in {"pass", "run"}:
                stats["yards_allowed"] += _number(row, "yards_gained")

        is_field_goal = _flag(row, "field_goal_attempt")
        is_extra_point = _flag(row, "extra_point_attempt")
        if is_field_goal or is_extra_point:
            kicker_id = _required_text(row, "kicker_player_id")
            kicker_team = _required_text(row, "posteam").upper()
            kicker_key = _week_key(row, kicker_id)
            record = kickers.setdefault(
                kicker_key,
                {
                    "player_id": kicker_id,
                    "gsis_id": kicker_id,
                    "display_name": _required_text(row, "kicker_player_name"),
                    "position": "K",
                    "nfl_team": kicker_team,
                    "source_updated_at": source_updated_at,
                },
            )
            if record["nfl_team"] != kicker_team:
                raise DataValidationError("kicker has inconsistent team within a source week")
            record["field_goal_attempts"] = _as_number(
                record.get("field_goal_attempts"), "field_goal_attempts"
            ) + float(is_field_goal)
            record["field_goals_made"] = _as_number(
                record.get("field_goals_made"), "field_goals_made"
            ) + float(is_field_goal and _text(row, "field_goal_result") == "made")
            record["extra_point_attempts"] = _as_number(
                record.get("extra_point_attempts"), "extra_point_attempts"
            ) + float(is_extra_point)
            record["extra_points_made"] = _as_number(
                record.get("extra_points_made"), "extra_points_made"
            ) + float(is_extra_point and _text(row, "extra_point_result") == "good")

    players: dict[str, dict[str, object]] = {}
    weeks: list[Mapping[str, object]] = []
    for (season, week, kicker_id), record in sorted(kickers.items()):
        players[kicker_id] = {
            key: value
            for key, value in record.items()
            if key
            in {
                "player_id",
                "gsis_id",
                "display_name",
                "position",
                "nfl_team",
                "source_updated_at",
            }
        }
        weeks.append(
            {
                **record,
                "season": season,
                "week": week,
                "active": True,
            }
        )
    for (season, week, team), stats in sorted(defenses.items()):
        defense_id = f"defense:{team}"
        defense_player = players.setdefault(
            defense_id,
            {
                "player_id": defense_id,
                "display_name": f"{team} Defense",
                "position": "DEF",
                "nfl_team": team,
                "valid_from_season": season,
                "valid_through_season": season,
                "source_updated_at": source_updated_at,
            },
        )
        defense_player["valid_from_season"] = min(
            _as_int(defense_player["valid_from_season"], "valid_from_season"), season
        )
        defense_player["valid_through_season"] = max(
            _as_int(defense_player["valid_through_season"], "valid_through_season"), season
        )
        points_allowed = 0.0
        for game_id in defense_games[(season, week, team)]:
            score = game_scores.get(game_id)
            if score is None:
                raise DataValidationError("defense game is missing final score evidence")
            home, away, home_score, away_score = score
            if team == home:
                points_allowed += away_score
            elif team == away:
                points_allowed += home_score
            else:
                raise DataValidationError("defense team is not part of its PBP game")
        weeks.append(
            {
                "player_id": defense_id,
                "season": season,
                "week": week,
                "position": "DEF",
                **stats,
                "points_allowed": points_allowed,
                "active": True,
                "source_updated_at": source_updated_at,
            }
        )
    return KDefSourceRows(
        players=tuple(players[key] for key in sorted(players)),
        weeks=tuple(
            sorted(weeks, key=lambda row: (str(row["player_id"]), row["season"], row["week"]))
        ),
    )
