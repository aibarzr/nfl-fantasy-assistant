"""Runtime assembly of reproducible recommendations from canonical draft state."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from nfl_fantasy_assistant.application.drafts import ApplicationError
from nfl_fantasy_assistant.application.ports import DraftRepository
from nfl_fantasy_assistant.data.runtime import ActivatedSleeperDataset, RuntimeRecommendationInput
from nfl_fantasy_assistant.domain.draft import (
    DraftSession,
    DraftStatus,
    RecommendationCandidate,
    RecommendationSnapshot,
)
from nfl_fantasy_assistant.models.draft_ranking import (
    DraftRankInput,
    RankingError,
    rank_draft_candidates,
)
from nfl_fantasy_assistant.models.replacement import ReplacementError, value_over_replacement


@dataclass(frozen=True, slots=True)
class RecommendationRuntime:
    """A single immutable Sleeper dataset's inputs and safe ranking entrypoint."""

    dataset: ActivatedSleeperDataset
    repository: DraftRepository
    top_n: int = 10

    def __post_init__(self) -> None:
        if not self.dataset.recommendations_ready:
            raise ValueError("recommendation runtime requires a dataset input artifact")

    @property
    def _by_id(self) -> dict[str, RuntimeRecommendationInput]:
        return {item.internal_player_id: item for item in self.dataset.recommendation_inputs}

    def generate(self, session: DraftSession) -> RecommendationSnapshot:
        """Persist Top-N only when every ranking input and draft fact is trustworthy."""
        if session.provider != "sleeper":
            raise ApplicationError(
                "recommendations_unavailable",
                "The active recommendation runtime is configured only for Sleeper.",
                503,
            )
        if (
            session.dataset_version,
            session.feature_version,
            session.model_version,
        ) != (
            self.dataset.dataset_version,
            self.dataset.feature_version,
            self.dataset.model_version,
        ):
            raise ApplicationError(
                "recommendation_runtime_version_conflict",
                "Draft provenance does not match the active Sleeper recommendation runtime.",
                409,
            )
        if session.status is not DraftStatus.ACTIVE or session.unresolved_observations:
            raise ApplicationError(
                "recommendations_not_current",
                "Recommendations require active, fully resolved canonical draft state.",
                503,
            )
        by_id = self._by_id
        drafted_positions: Counter[str] = Counter()
        for pick in session.accepted_picks:
            recommendation_input = by_id.get(pick.internal_player_id)
            if recommendation_input is not None:
                drafted_positions[recommendation_input.position] += 1
                continue
            identity = self.repository.get_player(pick.internal_player_id)
            if identity is None:
                raise ApplicationError(
                    "recommendations_not_current",
                    "An accepted pick has no exact immutable runtime identity.",
                    503,
                )
            drafted_positions[identity.position] += 1
        available_ids = tuple(
            sorted(set(by_id) - {pick.internal_player_id for pick in session.accepted_picks})
        )
        available = tuple(by_id[identifier] for identifier in available_ids)
        try:
            vor_by_id = {
                item.internal_player_id: item
                for item in value_over_replacement(
                    session.config,
                    (item.value for item in available),
                    drafted_positions,
                )
            }
            ranked = rank_draft_candidates(
                session,
                (
                    DraftRankInput(item.value, vor_by_id[item.internal_player_id], item.projection)
                    for item in available
                    if item.internal_player_id in vor_by_id
                ),
                {identifier: item.position for identifier, item in by_id.items()},
                top_n=self.top_n,
            )
        except (RankingError, ReplacementError, KeyError) as error:
            raise ApplicationError(
                "recommendation_runtime_invalid",
                "The active recommendation runtime cannot rank this canonical draft state.",
                503,
            ) from error
        snapshot = RecommendationSnapshot(
            snapshot_id=f"recommendation_{uuid4().hex}",
            draft_id=session.draft_id,
            canonical_revision=session.revision,
            generated_at=datetime.now(UTC),
            available_player_ids=available_ids,
            candidates=tuple(
                RecommendationCandidate(
                    internal_player_id=item.candidate.internal_player_id,
                    rank=item.candidate.rank,
                    draft_score=item.candidate.draft_score,
                    confidence=item.candidate.confidence,
                    components=item.candidate.components,
                    reason_codes=item.candidate.reason_codes,
                    reason_text=item.candidate.reason_text,
                    warnings=item.warnings,
                )
                for item in ranked
            ),
            config_version=session.config.config_version,
            dataset_version=session.dataset_version,
            feature_version=session.feature_version,
            model_version=session.model_version,
            source_updated_at={
                identifier: by_id[identifier].source_updated_at for identifier in available_ids
            },
        )
        self.repository.save_recommendation(snapshot)
        return snapshot
