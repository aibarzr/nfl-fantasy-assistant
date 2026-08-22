"""Dynamic replacement level and value-over-replacement calculations."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from math import ceil

from nfl_fantasy_assistant.domain.draft import LeagueConfig

from .valuation import PlayerValue


class ReplacementError(ValueError):
    """A replacement calculation lacks a legal, canonical pool/configuration."""


@dataclass(frozen=True, slots=True)
class ReplacementLevel:
    position: str
    value_score: float
    direct_demand: int
    flex_demand: int
    bench_demand: int
    drafted_count: int
    replacement_index: int


@dataclass(frozen=True, slots=True)
class ValueOverReplacement:
    internal_player_id: str
    position: str
    player_value: float
    replacement_value: float
    vor: float
    components: Mapping[str, float]


def _eligible_positions(config: LeagueConfig) -> tuple[str, ...]:
    return tuple(
        sorted({position for slot in config.roster_slots for position in slot.eligible_positions})
    )


def _position_demands(
    config: LeagueConfig,
    available: tuple[PlayerValue, ...],
    drafted_positions: Mapping[str, int],
    include_bench: bool,
    include_drafted: bool,
) -> dict[str, tuple[int, int, int, int]]:
    positions = _eligible_positions(config)
    if not positions:
        raise ReplacementError("league configuration has no eligible positions")
    direct: Counter[str] = Counter()
    flex_slots: list[frozenset[str]] = []
    bench_slots: list[frozenset[str]] = []
    for slot in config.roster_slots:
        if len(slot.eligible_positions) == 1 and not slot.is_bench:
            direct[next(iter(slot.eligible_positions))] += config.team_count
        elif slot.is_bench:
            bench_slots.append(slot.eligible_positions)
        else:
            flex_slots.append(slot.eligible_positions)
    available_count = Counter(player.position for player in available)
    flex_demand: Counter[str] = Counter()
    bench_demand: Counter[str] = Counter()
    for eligible in flex_slots:
        total = sum(available_count[position] for position in eligible)
        for position in eligible:
            share = available_count[position] / total if total else 1 / len(eligible)
            flex_demand[position] += ceil(config.team_count * share)
    if include_bench:
        for eligible in bench_slots:
            total = sum(available_count[position] for position in eligible)
            for position in eligible:
                share = available_count[position] / total if total else 1 / len(eligible)
                bench_demand[position] += ceil(config.team_count * share)
    return {
        position: (
            direct[position],
            flex_demand[position],
            bench_demand[position],
            drafted_positions.get(position, 0) if include_drafted else 0,
        )
        for position in positions
    }


def replacement_levels(
    config: LeagueConfig,
    available_values: Iterable[PlayerValue],
    drafted_positions: Mapping[str, int],
) -> dict[str, ReplacementLevel]:
    """Derive replacement thresholds from league demand, current pool, and accepted picks."""
    available = tuple(available_values)
    if len({player.internal_player_id for player in available}) != len(available):
        raise ReplacementError("available values require unique internal player IDs")
    demands = _position_demands(config, available, drafted_positions, True, True)
    result: dict[str, ReplacementLevel] = {}
    for position, (direct, flex, bench, drafted) in demands.items():
        values = sorted(
            (player.value_score for player in available if player.position == position),
            reverse=True,
        )
        if not values:
            continue
        index = min(len(values) - 1, max(0, direct + flex + bench - drafted - 1))
        result[position] = ReplacementLevel(
            position=position,
            value_score=values[index],
            direct_demand=direct,
            flex_demand=flex,
            bench_demand=bench,
            drafted_count=drafted,
            replacement_index=index,
        )
    return result


def static_replacement_levels(
    config: LeagueConfig, available_values: Iterable[PlayerValue]
) -> dict[str, ReplacementLevel]:
    """Declared comparison baseline: roster-start demand only, without state/bench dynamics."""
    available = tuple(available_values)
    demands = _position_demands(config, available, {}, False, False)
    result: dict[str, ReplacementLevel] = {}
    for position, (direct, flex, _, _) in demands.items():
        values = sorted(
            (player.value_score for player in available if player.position == position),
            reverse=True,
        )
        if values:
            index = min(len(values) - 1, max(0, direct + flex - 1))
            result[position] = ReplacementLevel(position, values[index], direct, flex, 0, 0, index)
    return result


def value_over_replacement(
    config: LeagueConfig,
    available_values: Iterable[PlayerValue],
    drafted_positions: Mapping[str, int],
) -> tuple[ValueOverReplacement, ...]:
    """Calculate VOR using valued player outputs, never raw features or historical rows."""
    available = tuple(available_values)
    levels = replacement_levels(config, available, drafted_positions)
    result: list[ValueOverReplacement] = []
    for player in available:
        level = levels.get(player.position)
        if level is None:
            continue
        result.append(
            ValueOverReplacement(
                internal_player_id=player.internal_player_id,
                position=player.position,
                player_value=player.value_score,
                replacement_value=level.value_score,
                vor=round(player.value_score - level.value_score, 6),
                components={
                    "direct_demand": float(level.direct_demand),
                    "flex_demand": float(level.flex_demand),
                    "bench_demand": float(level.bench_demand),
                    "drafted_count": float(level.drafted_count),
                    "replacement_index": float(level.replacement_index),
                },
            )
        )
    return tuple(sorted(result, key=lambda player: (-player.vor, player.internal_player_id)))
