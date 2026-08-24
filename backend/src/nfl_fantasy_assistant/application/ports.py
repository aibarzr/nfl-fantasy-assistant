"""Application-facing persistence contracts.

The application layer names the state it needs, while outer adapters choose transaction and
storage mechanics.  Keeping this protocol here prevents draft behavior from acquiring SQLite
coupling.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from nfl_fantasy_assistant.domain.draft import (
    DraftId,
    DraftSession,
    LeagueConfig,
    LeagueId,
    Player,
    PlayerStatusOverlay,
    RecommendationSnapshot,
)


class DraftRepository(Protocol):
    def migrate(self) -> None: ...

    def find_league_by_provider(
        self, provider: str, provider_league_id: str
    ) -> LeagueId | None: ...

    def save_league_identity(
        self, league_id: LeagueId, provider: str, provider_league_id: str, config: LeagueConfig
    ) -> None: ...

    def find_draft_by_provider(
        self, provider: str, provider_draft_id: str
    ) -> DraftSession | None: ...

    def get_draft(self, draft_id: DraftId) -> DraftSession | None: ...

    def save_draft(self, session: DraftSession) -> None: ...

    def save_player(self, player: Player) -> None: ...

    def get_player(self, internal_player_id: str) -> Player | None: ...

    def find_player_by_external_id(self, provider: str, external_id: str) -> Player | None: ...

    def save_event_outcome(
        self,
        draft_id: DraftId,
        event_id: str,
        fingerprint: str,
        outcome: str,
        resulting_revision: int,
    ) -> None: ...

    def get_event_outcome(
        self, draft_id: DraftId, event_id: str
    ) -> tuple[str, str, int] | None: ...

    def set_metadata(self, key: str, value: str) -> None: ...

    def get_metadata(self, key: str) -> str | None: ...

    def commit_transition(
        self,
        session: DraftSession,
        event_id: str | None = None,
        fingerprint: str | None = None,
        outcome: str | None = None,
    ) -> None: ...

    def save_recommendation(self, snapshot: RecommendationSnapshot) -> None: ...

    def latest_recommendation(self, draft_id: DraftId) -> RecommendationSnapshot | None: ...

    def save_status_overlay(self, overlay: PlayerStatusOverlay) -> bool: ...

    def latest_status_overlay(
        self, provider: str, dataset_version: str
    ) -> PlayerStatusOverlay | None: ...

    def commit_reconciliation(
        self,
        session: DraftSession,
        source: str,
        observed_at: datetime,
        declared_complete: bool,
        differences: Mapping[str, object],
        outcome: str,
    ) -> None: ...
