"""Deterministic, explainable draft scoring over current canonical state."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from nfl_fantasy_assistant.domain.draft import (
    DraftSession,
    DraftStatus,
    PlayerStatus,
    RecommendationCandidate,
)

from .projection import PlayerProjection
from .replacement import ValueOverReplacement
from .valuation import PlayerValue


class RankingError(ValueError):
    """A ranking request does not represent trusted canonical draft state."""


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize(values: Mapping[str, float]) -> dict[str, float]:
    if not values:
        return {}
    low, high = min(values.values()), max(values.values())
    if low == high:
        return {key: 0.5 for key in values}
    return {key: (value - low) / (high - low) for key, value in values.items()}


@dataclass(frozen=True, slots=True)
class DraftRankInput:
    player_value: PlayerValue
    vor: ValueOverReplacement
    projection: PlayerProjection
    historical_durability: float | None = None
    current_status: PlayerStatus = PlayerStatus.UNKNOWN

    def __post_init__(self) -> None:
        identifiers = {
            self.player_value.internal_player_id,
            self.vor.internal_player_id,
            self.projection.internal_player_id,
        }
        if (
            len(identifiers) != 1
            or len({self.player_value.position, self.vor.position, self.projection.position}) != 1
        ):
            raise RankingError("ranking inputs must join exactly by player ID and position")
        if self.historical_durability is not None and not 0 <= self.historical_durability <= 1:
            raise RankingError("historical durability must be a unit value when known")


@dataclass(frozen=True, slots=True)
class RankingParameters:
    ranking_version: str = "draft-ranking-v1"
    normalization_version: str = "draft-components-v1"
    risk_policy_version: str = "injury-risk-v1-warning-only"
    profiles: Mapping[str, Mapping[str, float]] = field(
        default_factory=lambda: {
            "early": {
                "vor": 0.45,
                "urgency": 0.20,
                "scarcity": 0.15,
                "market": 0.10,
                "roster": 0.05,
                "risk_upside": 0.05,
            },
            "middle": {
                "vor": 0.35,
                "urgency": 0.20,
                "scarcity": 0.20,
                "market": 0.10,
                "roster": 0.10,
                "risk_upside": 0.05,
            },
            "late": {
                "vor": 0.25,
                "urgency": 0.15,
                "scarcity": 0.15,
                "market": 0.05,
                "roster": 0.20,
                "risk_upside": 0.20,
            },
        }
    )

    def __post_init__(self) -> None:
        expected = {"vor", "urgency", "scarcity", "market", "roster", "risk_upside"}
        if (
            not self.ranking_version
            or not self.normalization_version
            or not self.risk_policy_version
            or set(self.profiles)
            != {
                "early",
                "middle",
                "late",
            }
        ):
            raise RankingError("ranking requires versioned early/middle/late profiles")
        for profile in self.profiles.values():
            if set(profile) != expected or abs(sum(profile.values()) - 1.0) > 0.000001:
                raise RankingError(
                    "ranking component profiles must include all components and sum to one"
                )


@dataclass(frozen=True, slots=True)
class RankedRecommendation:
    candidate: RecommendationCandidate
    warnings: tuple[str, ...]
    stage: str
    picks_until_next_turn: int
    ranking_version: str
    model_version: str
    feature_version: str
    dataset_version: str
    risk_policy_version: str


def _stage(session: DraftSession) -> str:
    round_number = max(1, (session.current_pick - 1) // session.config.team_count + 1)
    return "early" if round_number <= 3 else "middle" if round_number <= 8 else "late"


def _picks_until_next_turn(session: DraftSession) -> int:
    for index in range(session.current_pick - 1, len(session.draft_order)):
        if session.draft_order[index] == session.user_team_id:
            return index - (session.current_pick - 1)
    return 0


def _roster_need(
    session: DraftSession,
    inputs: tuple[DraftRankInput, ...],
    player_positions: Mapping[str, str],
) -> dict[str, float]:
    drafted_positions: Counter[str] = Counter()
    for pick in session.accepted_picks:
        if pick.team_id == session.user_team_id:
            position = player_positions.get(pick.internal_player_id)
            if position is None:
                raise RankingError(
                    "canonical roster positions are required for accepted user picks"
                )
            drafted_positions[position] += 1
    required: Counter[str] = Counter()
    for slot in session.config.starting_slots:
        if len(slot.eligible_positions) == 1:
            required[next(iter(slot.eligible_positions))] += 1
    deficits = {
        position: max(0, required[position] - drafted_positions[position])
        for position in {item.player_value.position for item in inputs}
    }
    max_deficit = max(deficits.values(), default=0)
    return {
        position: deficit / max_deficit if max_deficit else 0.0
        for position, deficit in deficits.items()
    }


def rank_draft_candidates(
    session: DraftSession,
    available_inputs: Iterable[DraftRankInput],
    player_positions: Mapping[str, str],
    parameters: RankingParameters | None = None,
    top_n: int = 10,
) -> tuple[RankedRecommendation, ...]:
    """Rank canonical availability with transparent deterministic components and explanations."""
    if session.status is not DraftStatus.ACTIVE:
        raise RankingError(
            "blocked, reconciling, discovered, or complete drafts cannot rank current players"
        )
    if top_n < 1:
        raise RankingError("Top-N must be positive")
    active_parameters = parameters or RankingParameters()
    inputs = tuple(available_inputs)
    identifiers = [item.player_value.internal_player_id for item in inputs]
    if len(identifiers) != len(set(identifiers)):
        raise RankingError("canonical availability contains duplicate player IDs")
    if {pick.internal_player_id for pick in session.accepted_picks} & set(identifiers):
        raise RankingError("drafted players cannot appear in canonical availability")
    stage = _stage(session)
    weights = active_parameters.profiles[stage]
    next_turn = _picks_until_next_turn(session)
    vor_scores = _normalize({item.player_value.internal_player_id: item.vor.vor for item in inputs})
    market_scores = {
        item.player_value.internal_player_id: item.player_value.components["market_prior"]
        for item in inputs
    }
    roster_scores = _roster_need(session, inputs, player_positions)
    position_vors: dict[str, list[float]] = {}
    for item in inputs:
        position_vors.setdefault(item.player_value.position, []).append(item.vor.vor)
    scarcity_scores: dict[str, float] = {}
    for position, values in position_vors.items():
        ordered = sorted(values, reverse=True)
        next_value = ordered[1] if len(ordered) > 1 else ordered[0]
        scarcity_scores[position] = max(0.0, ordered[0] - next_value)
    normalized_scarcity = _normalize(
        {
            item.player_value.internal_player_id: max(
                0.0, item.vor.vor - min(position_vors[item.player_value.position])
            )
            + scarcity_scores[item.player_value.position]
            for item in inputs
        }
    )
    recommendations: list[RankedRecommendation] = []
    for item in inputs:
        identifier = item.player_value.internal_player_id
        # Strong market signal, lower uncertainty, and a long wait increase deterministic urgency.
        survival = _clamp(
            item.player_value.components["market_prior"]
            * (1 - item.player_value.uncertainty)
            * (next_turn / max(1, session.config.team_count * 2))
        )
        urgency = 1 - survival
        upside = _clamp(
            (item.projection.ceiling_points - item.projection.expected_points) / 12.0
            + (1 - item.projection.confidence) * 0.25
        )
        components = {
            "vor": round(vor_scores[identifier], 6),
            "urgency": round(urgency, 6),
            "scarcity": round(normalized_scarcity[identifier], 6),
            "market": round(market_scores[identifier], 6),
            "roster": round(roster_scores.get(item.player_value.position, 0.0), 6),
            "risk_upside": round(upside, 6),
            "historical_durability": round(item.historical_durability or 0.0, 6),
            "current_status_risk": {
                PlayerStatus.HEALTHY: 0.0,
                PlayerStatus.LIMITED: 0.25,
                PlayerStatus.QUESTIONABLE: 0.5,
                PlayerStatus.DOUBTFUL: 0.75,
                PlayerStatus.OUT: 1.0,
                PlayerStatus.RESERVE: 1.0,
                PlayerStatus.INACTIVE: 1.0,
                PlayerStatus.UNKNOWN: 0.5,
            }[item.current_status],
        }
        score = round(sum(components[name] * weights[name] for name in weights), 6)
        reasons: list[str] = []
        if components["vor"] >= 0.75:
            reasons.append("high_vor")
        if components["urgency"] >= 0.65:
            reasons.append("next_turn_urgency")
        if components["scarcity"] >= 0.65:
            reasons.append("positional_scarcity")
        if components["roster"] >= 0.5:
            reasons.append("roster_need")
        if item.current_status is not PlayerStatus.HEALTHY:
            reasons.append(f"current_status_{item.current_status.value}")
        if item.historical_durability is not None and item.historical_durability < 0.75:
            reasons.append("low_historical_durability")
        if not reasons:
            reasons.append("balanced_value")
        warnings_list = [*item.player_value.warnings, *item.projection.warnings]
        confidence_multiplier = 1.0
        if item.current_status is PlayerStatus.UNKNOWN:
            warnings_list.append("current_status_unknown")
            confidence_multiplier *= 0.92
        elif item.current_status is not PlayerStatus.HEALTHY:
            warnings_list.append(f"current_status_{item.current_status.value}")
            confidence_multiplier *= 0.96
        if item.historical_durability is None:
            warnings_list.append("historical_durability_unknown")
            confidence_multiplier *= 0.92
        elif item.historical_durability < 0.75:
            warnings_list.append("low_historical_durability")
            confidence_multiplier *= 0.95
        warnings = tuple(sorted(set(warnings_list)))
        reason_text = "; ".join(reasons).replace("_", " ")
        recommendations.append(
            RankedRecommendation(
                candidate=RecommendationCandidate(
                    internal_player_id=identifier,
                    rank=0,
                    draft_score=score,
                    confidence=round(
                        _clamp(
                            (item.player_value.confidence + item.projection.confidence)
                            / 2
                            * confidence_multiplier
                        ),
                        3,
                    ),
                    components=components,
                    reason_codes=tuple(reasons),
                    reason_text=reason_text,
                ),
                warnings=warnings,
                stage=stage,
                picks_until_next_turn=next_turn,
                ranking_version=active_parameters.ranking_version,
                model_version=item.projection.model_version,
                feature_version=session.feature_version,
                dataset_version=session.dataset_version,
                risk_policy_version=active_parameters.risk_policy_version,
            )
        )
    ranked = sorted(
        recommendations,
        key=lambda item: (-item.candidate.draft_score, item.candidate.internal_player_id),
    )[:top_n]
    return tuple(
        RankedRecommendation(
            candidate=RecommendationCandidate(
                internal_player_id=item.candidate.internal_player_id,
                rank=index,
                draft_score=item.candidate.draft_score,
                confidence=item.candidate.confidence,
                components=item.candidate.components,
                reason_codes=item.candidate.reason_codes,
                reason_text=item.candidate.reason_text,
            ),
            warnings=item.warnings,
            stage=item.stage,
            picks_until_next_turn=item.picks_until_next_turn,
            ranking_version=item.ranking_version,
            model_version=item.model_version,
            feature_version=item.feature_version,
            dataset_version=item.dataset_version,
            risk_policy_version=item.risk_policy_version,
        )
        for index, item in enumerate(ranked, start=1)
    )
