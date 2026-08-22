"""Framework-independent draft state, invariants, and deterministic projections.

This module deliberately uses only standard-library value types.  HTTP, SQLite, and
prepared-data adapters translate at this boundary rather than leaking their records into
the canonical draft model.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType

from .scoring import ScoringError, validate_scoring_rules


class DomainError(ValueError):
    """A requested state transition violates a canonical draft invariant."""


class DraftStatus(StrEnum):
    DISCOVERED = "discovered"
    ACTIVE = "active"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    RECONCILING = "reconciling"


class IdentityState(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    CONFLICT = "conflict"


class AssetType(StrEnum):
    PLAYER = "player"
    TEAM_DEFENSE = "team_defense"


SUPPORTED_DRAFT_POSITIONS = frozenset({"QB", "RB", "WR", "TE", "K", "DEF"})


class ReconciliationState(StrEnum):
    CURRENT = "current"
    NEEDS_RECONCILIATION = "needs_reconciliation"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class DraftId:
    """Opaque internal draft identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("draft ID must be non-empty")


@dataclass(frozen=True, slots=True)
class LeagueId:
    """Opaque internal league identifier."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("league ID must be non-empty")


@dataclass(frozen=True, slots=True)
class Player:
    """Stable draftable asset; display attributes are never identity keys.

    The retained ``Player`` name is a compatibility boundary for persisted v1 records.  ``DEF``
    uses ``AssetType.TEAM_DEFENSE`` and never represents a fictional individual player.
    """

    internal_player_id: str
    external_ids: Mapping[str, str]
    display_name: str
    position: str
    nfl_team: str | None = None
    identity_state: IdentityState = IdentityState.RESOLVED
    asset_type: AssetType | None = None

    def __post_init__(self) -> None:
        if not self.internal_player_id.strip() or self.position not in SUPPORTED_DRAFT_POSITIONS:
            raise DomainError("player ID and position are required")
        if any(
            not provider or not external_id for provider, external_id in self.external_ids.items()
        ):
            raise DomainError("player external IDs must be non-empty provider/ID pairs")
        derived_asset_type = AssetType.TEAM_DEFENSE if self.position == "DEF" else AssetType.PLAYER
        if self.asset_type is not None and self.asset_type is not derived_asset_type:
            raise DomainError("asset type must agree with position")
        if derived_asset_type is AssetType.TEAM_DEFENSE and not self.nfl_team:
            raise DomainError("team-defense assets require an NFL team")
        object.__setattr__(self, "external_ids", MappingProxyType(dict(self.external_ids)))
        object.__setattr__(self, "asset_type", derived_asset_type)

    @property
    def internal_asset_id(self) -> str:
        """Neutral terminology while v1 persistence retains ``internal_player_id``."""
        return self.internal_player_id


DraftableAsset = Player


@dataclass(frozen=True, slots=True)
class PlayerReference:
    """Neutral external player reference from an untrusted observation."""

    provider: str
    external_id: str
    name: str | None = None
    position: str | None = None
    nfl_team: str | None = None

    @property
    def asset_type(self) -> AssetType | None:
        if self.position is None:
            return None
        return AssetType.TEAM_DEFENSE if self.position == "DEF" else AssetType.PLAYER

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.external_id.strip():
            raise DomainError("player reference requires provider and external ID")
        if self.position is not None and self.position not in SUPPORTED_DRAFT_POSITIONS:
            raise DomainError("player reference position is unsupported")


@dataclass(frozen=True, slots=True)
class RosterSlot:
    """One configured roster slot and its legal positions."""

    name: str
    eligible_positions: frozenset[str]
    is_bench: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.eligible_positions:
            raise DomainError("roster slots require a name and at least one eligible position")
        unsupported = self.eligible_positions - SUPPORTED_DRAFT_POSITIONS
        if unsupported:
            raise DomainError(f"roster slot has unsupported positions: {sorted(unsupported)}")


@dataclass(frozen=True, slots=True)
class LeagueConfig:
    """Immutable semantic league configuration pinned by every active draft."""

    config_version: str
    team_count: int
    draft_type: str
    roster_slots: tuple[RosterSlot, ...]
    scoring_rules: Mapping[str, float]
    superflex: bool = False
    te_premium: float = 0.0

    def __post_init__(self) -> None:
        if not self.config_version.strip() or self.team_count < 2:
            raise DomainError("league configuration requires a version and at least two teams")
        if self.draft_type != "snake":
            raise DomainError("only snake drafts are supported")
        if not self.roster_slots:
            raise DomainError("league configuration requires roster slots")
        if not all(isinstance(points, int | float) for points in self.scoring_rules.values()):
            raise DomainError("scoring rules must be numeric")
        try:
            validate_scoring_rules(self.scoring_rules)
        except ScoringError as error:
            raise DomainError(str(error)) from error
        if self.te_premium < 0:
            raise DomainError("TE premium cannot be negative")
        object.__setattr__(self, "scoring_rules", MappingProxyType(dict(self.scoring_rules)))

    @property
    def starting_slots(self) -> tuple[RosterSlot, ...]:
        return tuple(slot for slot in self.roster_slots if not slot.is_bench)


@dataclass(frozen=True, slots=True)
class DraftPick:
    """One accepted, identity-resolved pick in canonical state."""

    overall_pick: int
    team_id: str
    internal_player_id: str
    source: str
    observed_at: datetime
    event_id: str | None = None

    def __post_init__(self) -> None:
        if self.overall_pick < 1 or not self.team_id or not self.internal_player_id:
            raise DomainError("pick number, team, and internal player ID are required")
        if not self.source:
            raise DomainError("accepted picks retain their observation source")
        if self.observed_at.tzinfo is None:
            raise DomainError("pick observation time must include a timezone")


@dataclass(frozen=True, slots=True)
class UnresolvedObservation:
    event_id: str | None
    overall_pick: int
    team_id: str
    reference: PlayerReference
    source: str
    observed_at: datetime
    reason: str


@dataclass(frozen=True, slots=True)
class RosterAssignment:
    player_id: str
    slot_name: str


@dataclass(frozen=True, slots=True)
class TeamRoster:
    """Derived roster membership and legal slot assignments for one configured team."""

    team_id: str
    player_ids: tuple[str, ...]
    assignments: tuple[RosterAssignment, ...]


@dataclass(frozen=True, slots=True)
class DraftSession:
    """Persisted canonical state for a single independently identified draft."""

    draft_id: DraftId
    league_id: LeagueId
    provider: str
    provider_draft_id: str
    config: LeagueConfig
    user_team_id: str
    user_slot: int
    draft_order: tuple[str, ...]
    dataset_version: str
    feature_version: str
    model_version: str
    status: DraftStatus = DraftStatus.DISCOVERED
    reconciliation_state: ReconciliationState = ReconciliationState.CURRENT
    revision: int = 0
    accepted_picks: tuple[DraftPick, ...] = ()
    unresolved_observations: tuple[UnresolvedObservation, ...] = ()
    issues: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.provider or not self.provider_draft_id:
            raise DomainError("provider and provider draft ID are required")
        if self.user_team_id not in set(self.draft_order):
            raise DomainError("user team must appear in the configured draft order")
        if not 1 <= self.user_slot <= len(self.draft_order):
            raise DomainError("user slot must be a valid overall draft-order slot")
        if self.draft_order[self.user_slot - 1] != self.user_team_id:
            raise DomainError("user team and user slot must agree")
        if len(self.draft_order) % self.config.team_count != 0:
            raise DomainError("draft order must contain complete configured rounds")
        if len(set(self.draft_order[: self.config.team_count])) != self.config.team_count:
            raise DomainError("each configured team must appear once in the opening round")
        if not self.dataset_version or not self.feature_version or not self.model_version:
            raise DomainError("draft inputs must be pinned to non-empty versions")
        validate_picks(self.draft_order, self.accepted_picks)
        if self.status is DraftStatus.COMPLETE and len(self.accepted_picks) != len(
            self.draft_order
        ):
            raise DomainError("only a fully drafted session may be complete")

    @property
    def provider_key(self) -> tuple[str, str]:
        return self.provider, self.provider_draft_id

    @property
    def current_pick(self) -> int:
        for overall_pick in range(1, len(self.draft_order) + 1):
            if overall_pick not in {pick.overall_pick for pick in self.accepted_picks}:
                return overall_pick
        return len(self.draft_order) + 1


@dataclass(frozen=True, slots=True)
class RecommendationCandidate:
    internal_player_id: str
    rank: int
    draft_score: float
    confidence: float
    components: Mapping[str, float]
    reason_codes: tuple[str, ...]
    reason_text: str
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationSnapshot:
    """Durable result/provenance required to reproduce a published recommendation."""

    snapshot_id: str
    draft_id: DraftId
    canonical_revision: int
    generated_at: datetime
    available_player_ids: tuple[str, ...]
    candidates: tuple[RecommendationCandidate, ...]
    config_version: str
    dataset_version: str
    feature_version: str
    model_version: str
    source_updated_at: Mapping[str, str]
    is_current: bool = True
    chosen_player_id: str | None = None

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None or not self.snapshot_id:
            raise DomainError("recommendation snapshots need an ID and UTC-aware timestamp")
        if self.canonical_revision < 0 or not self.is_current:
            raise DomainError("only current canonical recommendation snapshots can be published")
        if not all(
            (self.config_version, self.dataset_version, self.feature_version, self.model_version)
        ):
            raise DomainError("recommendation provenance requires all pinned versions")
        if tuple(sorted(self.available_player_ids)) != self.available_player_ids:
            raise DomainError("available player IDs must be stable sorted order")
        object.__setattr__(
            self, "source_updated_at", MappingProxyType(dict(self.source_updated_at))
        )


def validate_picks(draft_order: tuple[str, ...], picks: Iterable[DraftPick]) -> None:
    """Validate unique pick/player/order invariants independently of persistence."""
    pick_rows = tuple(picks)
    overall_picks = [pick.overall_pick for pick in pick_rows]
    players = [pick.internal_player_id for pick in pick_rows]
    if len(overall_picks) != len(set(overall_picks)):
        raise DomainError("overall picks must be unique")
    if len(players) != len(set(players)):
        raise DomainError("a player may be drafted at most once")
    for pick in pick_rows:
        if pick.overall_pick > len(draft_order):
            raise DomainError("pick exceeds configured draft order")
        if draft_order[pick.overall_pick - 1] != pick.team_id:
            raise DomainError("pick team does not match configured draft order")


def apply_pick(session: DraftSession, pick: DraftPick) -> DraftSession:
    """Apply one validated pick and expose reconciliation when predecessors are missing."""
    if session.status is DraftStatus.COMPLETE:
        raise DomainError("completed drafts accept no new picks")
    if session.status is DraftStatus.BLOCKED:
        raise DomainError("blocked drafts cannot accept trusted picks")
    validate_picks(session.draft_order, (*session.accepted_picks, pick))
    missing_predecessor = any(
        number not in {accepted.overall_pick for accepted in session.accepted_picks}
        for number in range(1, pick.overall_pick)
    )
    picks = tuple(sorted((*session.accepted_picks, pick), key=lambda item: item.overall_pick))
    complete = len(picks) == len(session.draft_order)
    status = (
        DraftStatus.COMPLETE
        if complete
        else DraftStatus.RECONCILING
        if missing_predecessor
        else DraftStatus.ACTIVE
    )
    reconciliation = (
        ReconciliationState.NEEDS_RECONCILIATION
        if missing_predecessor
        else ReconciliationState.CURRENT
    )
    return replace(
        session,
        accepted_picks=picks,
        status=status,
        reconciliation_state=reconciliation,
        revision=session.revision + 1,
    )


def add_unresolved_observation(
    session: DraftSession, observation: UnresolvedObservation
) -> DraftSession:
    """Retain an unsafe identity observation without guessing a drafted player."""
    return replace(
        session,
        unresolved_observations=(*session.unresolved_observations, observation),
        status=DraftStatus.RECONCILING,
        reconciliation_state=ReconciliationState.NEEDS_RECONCILIATION,
        revision=session.revision + 1,
    )


def block_session(session: DraftSession, issue: str) -> DraftSession:
    """Preserve history while preventing fresh recommendations after a material conflict."""
    return replace(
        session,
        status=DraftStatus.BLOCKED,
        reconciliation_state=ReconciliationState.BLOCKED,
        issues=tuple(sorted(set((*session.issues, issue)))),
        revision=session.revision + 1,
    )


def derive_availability(
    pool_player_ids: Iterable[str], picks: Iterable[DraftPick]
) -> tuple[str, ...]:
    """Return deterministic pool availability without removing unresolved observations."""
    pool = tuple(pool_player_ids)
    if len(pool) != len(set(pool)):
        raise DomainError("prepared player pool contains duplicate internal IDs")
    drafted = {pick.internal_player_id for pick in picks}
    return tuple(sorted(player_id for player_id in pool if player_id not in drafted))


def derive_rosters(session: DraftSession, players: Mapping[str, Player]) -> tuple[TeamRoster, ...]:
    """Assign drafted players deterministically to the first legal configured slot.

    A player's roster membership is unconditional once a pick is accepted.  If all starting
    slots compatible with that player are full, it uses a legal bench slot.  Configurations
    that cannot accommodate an accepted player are invalid rather than silently inventing a slot.
    """
    per_team: dict[str, list[DraftPick]] = defaultdict(list)
    for pick in sorted(session.accepted_picks, key=lambda item: item.overall_pick):
        per_team[pick.team_id].append(pick)
    result: list[TeamRoster] = []
    for team_id in dict.fromkeys(session.draft_order):
        available_slots = list(session.config.roster_slots)
        assignments: list[RosterAssignment] = []
        player_ids: list[str] = []
        for pick in per_team[team_id]:
            player = players.get(pick.internal_player_id)
            if player is None:
                raise DomainError("accepted picks must reference known internal players")
            matches = [
                (index, slot)
                for index, slot in enumerate(available_slots)
                if player.position in slot.eligible_positions
            ]
            if not matches:
                raise DomainError("accepted player cannot be assigned to a legal roster slot")
            index, slot = matches[0]
            available_slots.pop(index)
            player_ids.append(player.internal_player_id)
            assignments.append(RosterAssignment(player.internal_player_id, slot.name))
        result.append(TeamRoster(team_id, tuple(player_ids), tuple(assignments)))
    return tuple(result)
