"""Auditable provider-to-internal identity resolution without name guessing."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from .curation import CuratedPlayer
from .errors import DataValidationError

IDENTITY_RULE_VERSION = "1"


@dataclass(frozen=True, slots=True)
class ExternalReference:
    provider: str
    external_id: str | None
    display_name: str | None = None
    nfl_team: str | None = None
    position: str | None = None


@dataclass(frozen=True, slots=True)
class IdentityMapping:
    provider: str
    external_id: str
    internal_player_id: str
    method: str
    provenance: str
    state: str = "accepted"


@dataclass(frozen=True, slots=True)
class ManualOverride:
    provider: str
    external_id: str
    internal_player_id: str
    reason: str
    provenance: str
    created_at: str
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class Resolution:
    state: str
    internal_player_id: str | None
    method: str | None
    evidence: str
    candidates: tuple[str, ...] = ()


def _internal_id(player: CuratedPlayer) -> str:
    anchor = player.gsis_id or player.source_player_id
    digest = hashlib.sha256(f"nfl-fantasy-assistant:{anchor}".encode()).hexdigest()[:24]
    return f"player-{digest}"


def normalize_name(name: str) -> str:
    simplified = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    simplified = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", simplified)
    return re.sub(r"[^a-z0-9]", "", simplified)


class IdentityPipeline:
    """Resolves exact IDs first and quarantines ambiguity as a result, not a mutation."""

    def __init__(
        self,
        players: Iterable[CuratedPlayer],
        mappings: Iterable[IdentityMapping] = (),
        overrides: Iterable[ManualOverride] = (),
    ) -> None:
        self._players = {player.source_player_id: player for player in players}
        self._internal = {
            source_id: _internal_id(player) for source_id, player in self._players.items()
        }
        self._exact: dict[tuple[str, str], IdentityMapping] = {}
        self._overrides: dict[tuple[str, str], ManualOverride] = {}
        for mapping in mappings:
            key = (mapping.provider, mapping.external_id)
            if key in self._exact:
                raise DataValidationError(f"duplicate provider ID: {key}")
            self._exact[key] = mapping
        for override in overrides:
            if not override.reason or not override.provenance or not override.created_at:
                raise DataValidationError(
                    "manual override requires reason, provenance, and timestamp"
                )
            key = (override.provider, override.external_id)
            if key in self._overrides:
                raise DataValidationError(f"duplicate manual override: {key}")
            self._overrides[key] = override

    @classmethod
    def from_players(
        cls, players: Iterable[CuratedPlayer], provider: str = "nflverse"
    ) -> IdentityPipeline:
        materialized = tuple(players)
        mappings: list[IdentityMapping] = []
        for player in materialized:
            identifier = player.gsis_id or player.source_player_id
            mappings.append(
                IdentityMapping(
                    provider=provider,
                    external_id=identifier,
                    internal_player_id=_internal_id(player),
                    method="authoritative_gsis" if player.gsis_id else "source_stable_id",
                    provenance=f"curated:{player.lineage_manifest_id}",
                )
            )
        return cls(materialized, mappings)

    def resolve(self, reference: ExternalReference) -> Resolution:
        if reference.external_id:
            key = (reference.provider, reference.external_id)
            override = self._overrides.get(key)
            if override:
                return Resolution(
                    "resolved", override.internal_player_id, "manual_override", override.provenance
                )
            exact = self._exact.get(key)
            if exact:
                return Resolution(
                    "resolved", exact.internal_player_id, exact.method, exact.provenance
                )

        if not reference.display_name:
            return Resolution("unresolved", None, None, "missing external ID and display evidence")
        candidates = [
            (source_id, player)
            for source_id, player in self._players.items()
            if normalize_name(player.display_name) == normalize_name(reference.display_name)
        ]
        corroborated = [
            source_id
            for source_id, player in candidates
            if reference.position == player.position and reference.nfl_team == player.nfl_team
        ]
        if len(corroborated) == 1:
            source_id = corroborated[0]
            return Resolution(
                "resolved",
                self._internal[source_id],
                f"normalized_name_v{IDENTITY_RULE_VERSION}",
                "single team-and-position corroborated normalized-name candidate",
            )
        candidate_ids = tuple(sorted(self._internal[source_id] for source_id, _ in candidates))
        state = "conflict" if candidate_ids else "unresolved"
        return Resolution(state, None, None, "name candidates require corroboration", candidate_ids)

    def mappings(self) -> tuple[IdentityMapping, ...]:
        return tuple(sorted(self._exact.values(), key=lambda row: (row.provider, row.external_id)))


def manual_override(
    provider: str,
    external_id: str,
    internal_player_id: str,
    reason: str,
    provenance: str,
    supersedes: str | None = None,
) -> ManualOverride:
    return ManualOverride(
        provider=provider,
        external_id=external_id,
        internal_player_id=internal_player_id,
        reason=reason,
        provenance=provenance,
        created_at=datetime.now(UTC).isoformat(),
        supersedes=supersedes,
    )
