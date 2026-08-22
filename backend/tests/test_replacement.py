from __future__ import annotations

from nfl_fantasy_assistant.domain.draft import LeagueConfig, RosterSlot
from nfl_fantasy_assistant.models.replacement import (
    replacement_levels,
    static_replacement_levels,
    value_over_replacement,
)
from nfl_fantasy_assistant.models.valuation import PlayerValue


def config(team_count: int, superflex: bool = False) -> LeagueConfig:
    flex = frozenset({"QB", "RB", "WR", "TE"} if superflex else {"RB", "WR", "TE"})
    return LeagueConfig(
        f"config-{team_count}-{superflex}",
        team_count,
        "snake",
        (
            RosterSlot("QB", frozenset({"QB"})),
            RosterSlot("RB", frozenset({"RB"})),
            RosterSlot("WR", frozenset({"WR"})),
            RosterSlot("TE", frozenset({"TE"})),
            RosterSlot("FLEX", flex),
            RosterSlot("BN", frozenset({"QB", "RB", "WR", "TE"}), is_bench=True),
        ),
        {},
        superflex=superflex,
    )


def values() -> tuple[PlayerValue, ...]:
    rows: list[PlayerValue] = []
    for position, start in (("QB", 0.95), ("RB", 0.9), ("WR", 0.88), ("TE", 0.7)):
        for index in range(30):
            rows.append(
                PlayerValue(
                    f"{position}-{index}",
                    position,
                    start - index * 0.02,
                    0.8,
                    0.1,
                    {},
                    (),
                    "value-v1",
                    "value-minmax-v1",
                )
            )
    return tuple(rows)


def test_replacement_responds_to_league_size_bench_flex_and_drafted_state() -> None:
    pool = values()
    ten = replacement_levels(config(10), pool, {})
    twelve = replacement_levels(config(12), pool, {})
    superflex = replacement_levels(config(12, True), pool, {})
    drafted = replacement_levels(config(12), pool, {"RB": 8})
    assert twelve["RB"].replacement_index > ten["RB"].replacement_index
    assert superflex["QB"].flex_demand > twelve["QB"].flex_demand
    assert drafted["RB"].replacement_index < twelve["RB"].replacement_index
    assert twelve["RB"].bench_demand > 0


def test_vor_uses_values_and_declared_static_baseline_not_raw_history() -> None:
    pool = values()
    dynamic = replacement_levels(config(12), pool, {})
    static = static_replacement_levels(config(12), pool)
    vor = value_over_replacement(config(12), pool, {})
    assert dynamic["RB"].value_score != static["RB"].value_score
    assert vor[0].player_value == pool[0].value_score or vor[0].vor >= vor[-1].vor
    assert "replacement_index" in vor[0].components
    assert vor == value_over_replacement(config(12), pool, {})
