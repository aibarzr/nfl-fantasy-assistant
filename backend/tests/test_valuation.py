from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nfl_fantasy_assistant.models.projection import PlayerProjection
from nfl_fantasy_assistant.models.valuation import (
    MarketPrior,
    ValuationError,
    ValueInput,
    value_players,
)

NOW = datetime(2026, 8, 1, tzinfo=UTC)


def projection(identifier: str, points: float, confidence: float = 0.8) -> PlayerProjection:
    return PlayerProjection(
        identifier,
        "RB",
        points,
        points - 3,
        points + 3,
        confidence,
        {"usage": 0.5},
        (),
        "projection-v1",
        "semantic-v1",
    )


def test_fresh_market_blends_own_model_and_ecr_without_becoming_ecr_only() -> None:
    values = value_players(
        (
            ValueInput(projection("own-best", 20), MarketPrior(ecr_rank=100, updated_at=NOW)),
            ValueInput(projection("market-best", 10), MarketPrior(ecr_rank=1, updated_at=NOW)),
        ),
        now=NOW,
    )
    by_id = {item.internal_player_id: item for item in values}
    assert by_id["own-best"].components["own_model_weight"] == pytest.approx(0.65)
    assert by_id["own-best"].components["market_weight"] == pytest.approx(0.35)
    assert by_id["own-best"].value_score > 0
    assert by_id["market-best"].value_score > 0
    assert [item.internal_player_id for item in values] != ["market-best", "own-best"]


def test_missing_and_stale_market_are_explicit_fallbacks_not_zeroes() -> None:
    values = value_players(
        (
            ValueInput(projection("missing", 20)),
            ValueInput(
                projection("stale", 15),
                MarketPrior(ecr_rank=1, updated_at=NOW - timedelta(days=8)),
            ),
        ),
        now=NOW,
    )
    by_id = {item.internal_player_id: item for item in values}
    assert "missing_market" in by_id["missing"].warnings
    assert by_id["missing"].components["market_prior"] == by_id["missing"].components["own_model"]
    assert "stale_market" in by_id["stale"].warnings
    assert by_id["stale"].components["market_weight"] == pytest.approx(0.14)


def test_dispersion_movement_and_replay_are_inspectable_and_deterministic() -> None:
    input_row = ValueInput(
        projection("moving", 18),
        MarketPrior(
            ecr_rank=10,
            best_rank=1,
            worst_rank=80,
            rank_movement=20,
            updated_at=NOW,
        ),
    )
    first = value_players((input_row,), now=NOW)
    assert first == value_players((input_row,), now=NOW)
    assert first[0].uncertainty > 0
    assert first[0].components["market_dispersion"] > 0
    assert first[0].components["market_movement"] > 0


def test_valuation_rejects_bad_market_and_duplicate_identity() -> None:
    with pytest.raises(ValuationError, match="positive"):
        MarketPrior(ecr_rank=0)
    with pytest.raises(ValuationError, match="unique"):
        value_players(
            (ValueInput(projection("same", 10)), ValueInput(projection("same", 12))), now=NOW
        )
