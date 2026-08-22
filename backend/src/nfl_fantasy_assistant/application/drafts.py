"""Use cases for initialization, observations, reconciliation, and draft projections."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from nfl_fantasy_assistant.application.ports import DraftRepository
from nfl_fantasy_assistant.domain.draft import (
    DomainError,
    DraftId,
    DraftPick,
    DraftSession,
    DraftStatus,
    LeagueConfig,
    LeagueId,
    PlayerReference,
    ReconciliationState,
    TeamRoster,
    UnresolvedObservation,
    add_unresolved_observation,
    apply_pick,
    block_session,
    derive_availability,
    derive_rosters,
)


class ApplicationError(ValueError):
    """Stable application failure mapped by the HTTP adapter without implementation details."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class ObservedPick:
    overall_pick: int
    team_id: str
    player: PlayerReference


@dataclass(frozen=True, slots=True)
class DraftEvent:
    event_id: str
    observed_at: datetime
    surface: str
    league_provider: str
    pick: ObservedPick
    protocol_version: str = "v1"


@dataclass(frozen=True, slots=True)
class DraftSnapshot:
    source: str
    observed_at: datetime
    declared_complete: bool
    picks: tuple[ObservedPick, ...]


@dataclass(frozen=True, slots=True)
class EventResult:
    outcome: str
    revision: int
    replayed: bool
    session: DraftSession


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    outcome: str
    revision: int
    differences: Mapping[str, object]
    session: DraftSession


def _fingerprint(event: DraftEvent) -> str:
    payload = {
        "protocol_version": event.protocol_version,
        "surface": event.surface,
        "league_provider": event.league_provider,
        "pick": {
            "overall_pick": event.pick.overall_pick,
            "team_id": event.pick.team_id,
            "player": {
                "provider": event.pick.player.provider,
                "external_id": event.pick.player.external_id,
            },
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class DraftService:
    """Coordinates pure domain transitions through an injected repository port."""

    def __init__(self, repository: DraftRepository) -> None:
        self._repository = repository

    def register_league(
        self, provider: str, provider_league_id: str, config: LeagueConfig
    ) -> LeagueId:
        existing = self._repository.find_league_by_provider(provider, provider_league_id)
        league_id = existing or LeagueId(f"league_{uuid4().hex}")
        try:
            self._repository.save_league_identity(league_id, provider, provider_league_id, config)
        except Exception as error:
            raise ApplicationError(
                "league_conflict", "League configuration conflicts with canonical state.", 409
            ) from error
        return league_id

    def initialize_or_resume(
        self,
        league_id: LeagueId,
        provider: str,
        provider_draft_id: str,
        config: LeagueConfig,
        user_team_id: str,
        user_slot: int,
        draft_order: tuple[str, ...],
        dataset_version: str,
        feature_version: str,
        model_version: str,
        initial_picks: tuple[ObservedPick, ...] = (),
    ) -> DraftSession:
        if config.team_count != 8:
            raise ApplicationError(
                "unsupported_league_configuration",
                "Only the MVP 8-team snake configuration is supported.",
                400,
            )
        existing = self._repository.find_draft_by_provider(provider, provider_draft_id)
        if existing is not None:
            if existing.league_id != league_id or (
                existing.dataset_version,
                existing.feature_version,
                existing.model_version,
            ) != (dataset_version, feature_version, model_version):
                raise ApplicationError(
                    "draft_initialization_conflict",
                    "Existing draft has incompatible immutable configuration or pinned versions.",
                    409,
                )
            return existing
        try:
            state = DraftSession(
                draft_id=DraftId(f"draft_{uuid4().hex}"),
                league_id=league_id,
                provider=provider,
                provider_draft_id=provider_draft_id,
                config=config,
                user_team_id=user_team_id,
                user_slot=user_slot,
                draft_order=draft_order,
                dataset_version=dataset_version,
                feature_version=feature_version,
                model_version=model_version,
                status=DraftStatus.ACTIVE,
            )
            for observed in sorted(initial_picks, key=lambda item: item.overall_pick):
                state = self._apply_observed_pick(
                    state, observed, "initial_snapshot", None, datetime.now(UTC)
                )
            self._repository.save_draft(state)
            return state
        except DomainError as error:
            raise ApplicationError("invalid_draft_configuration", str(error), 400) from error

    def ingest_event(self, draft_id: DraftId, event: DraftEvent) -> EventResult:
        state = self._require_draft(draft_id)
        if event.league_provider != state.provider:
            raise ApplicationError(
                "provider_mismatch", "Observation provider does not match draft provider."
            )
        fingerprint = _fingerprint(event)
        recorded = self._repository.get_event_outcome(draft_id, event.event_id)
        if recorded is not None:
            prior_fingerprint, outcome, revision = recorded
            if prior_fingerprint != fingerprint:
                raise ApplicationError(
                    "event_id_conflict", "The event ID was already used with different data.", 409
                )
            return EventResult(outcome, revision, True, state)
        try:
            updated = self._apply_observed_pick(
                state, event.pick, event.surface, event.event_id, event.observed_at
            )
            outcome = (
                "accepted_needs_reconciliation"
                if updated.reconciliation_state is ReconciliationState.NEEDS_RECONCILIATION
                else "accepted"
            )
            self._repository.commit_transition(updated, event.event_id, fingerprint, outcome)
            return EventResult(outcome, updated.revision, False, updated)
        except DomainError as error:
            raise ApplicationError("invalid_draft_event", str(error), 409) from error

    def reconcile(self, draft_id: DraftId, snapshot: DraftSnapshot) -> ReconciliationResult:
        state = self._require_draft(draft_id)
        observed_by_pick = {pick.overall_pick: pick for pick in snapshot.picks}
        if len(observed_by_pick) != len(snapshot.picks):
            raise ApplicationError("invalid_snapshot", "Snapshot contains duplicate overall picks.")
        accepted_by_pick = {pick.overall_pick: pick for pick in state.accepted_picks}
        differences: dict[str, list[int]] = {
            "identical": [],
            "missing": [],
            "partial": [],
            "conflicts": [],
            "unresolved": [],
        }
        updated = state
        for number, accepted in accepted_by_pick.items():
            observed = observed_by_pick.get(number)
            if observed is None:
                differences["partial"].append(number)
                continue
            resolved = self._repository.find_player_by_external_id(
                observed.player.provider, observed.player.external_id
            )
            if resolved is None:
                differences["unresolved"].append(number)
            elif (
                observed.team_id != accepted.team_id
                or resolved.internal_player_id != accepted.internal_player_id
            ):
                differences["conflicts"].append(number)
            else:
                differences["identical"].append(number)
        if differences["conflicts"]:
            updated = block_session(state, "snapshot_conflict")
            self._repository.commit_reconciliation(
                updated,
                snapshot.source,
                snapshot.observed_at,
                snapshot.declared_complete,
                differences,
                "conflict",
            )
            return ReconciliationResult("conflict", updated.revision, differences, updated)
        for number in sorted(set(observed_by_pick) - set(accepted_by_pick)):
            observed = observed_by_pick[number]
            before = updated
            updated = self._apply_observed_pick(
                updated, observed, snapshot.source, None, snapshot.observed_at
            )
            if updated is not before:
                differences["missing"].append(number)
        outcome = (
            "reconciled"
            if differences["missing"]
            else "partial"
            if differences["partial"]
            else "identical"
        )
        self._repository.commit_reconciliation(
            updated,
            snapshot.source,
            snapshot.observed_at,
            snapshot.declared_complete,
            differences,
            outcome,
        )
        return ReconciliationResult(outcome, updated.revision, differences, updated)

    def availability(self, draft_id: DraftId, pool_player_ids: tuple[str, ...]) -> tuple[str, ...]:
        state = self._require_draft(draft_id)
        return derive_availability(pool_player_ids, state.accepted_picks)

    def rosters(self, draft_id: DraftId) -> tuple[TeamRoster, ...]:
        state = self._require_draft(draft_id)
        players = {
            pick.internal_player_id: player
            for pick in state.accepted_picks
            if (player := self._repository.get_player(pick.internal_player_id)) is not None
        }
        return derive_rosters(state, players)

    def _apply_observed_pick(
        self,
        state: DraftSession,
        observed: ObservedPick,
        source: str,
        event_id: str | None,
        observed_at: datetime,
    ) -> DraftSession:
        player = self._repository.find_player_by_external_id(
            observed.player.provider, observed.player.external_id
        )
        if player is None:
            return add_unresolved_observation(
                state,
                UnresolvedObservation(
                    event_id=event_id,
                    overall_pick=observed.overall_pick,
                    team_id=observed.team_id,
                    reference=observed.player,
                    source=source,
                    observed_at=observed_at,
                    reason="unknown_player",
                ),
            )
        return apply_pick(
            state,
            DraftPick(
                observed.overall_pick,
                observed.team_id,
                player.internal_player_id,
                source,
                observed_at,
                event_id,
            ),
        )

    def _require_draft(self, draft_id: DraftId) -> DraftSession:
        state = self._repository.get_draft(draft_id)
        if state is None:
            raise ApplicationError("draft_not_found", "The draft does not exist.", 404)
        return state
