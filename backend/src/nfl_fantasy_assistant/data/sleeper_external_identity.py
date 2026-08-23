"""Local, explicitly reviewed Wikidata identity candidates for Sleeper observations."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .curation import SUPPORTED_POSITIONS
from .errors import DataValidationError
from .identity import IdentityMapping
from .sleeper_identity import SleeperCatalogRecord, SleeperExternalObservedIdentity

WIKIDATA_ACTION_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_USER_AGENT = "nfl-fantasy-assistant/0.1 private-identity-review"


@dataclass(frozen=True, slots=True)
class SleeperExternalIdentityCandidate:
    external_id: str
    internal_player_id: str
    position: str
    nfl_team: str | None
    wikidata_entity_id: str
    espn_id: str | None
    nfl_com_id: str | None
    provider_display_name: str
    candidate_label: str
    source_retrieved_at: str
    entity_revision: int | None


@dataclass(frozen=True, slots=True)
class SleeperExternalIdentityDecision:
    external_id: str
    internal_player_id: str
    reviewer: str
    reviewed_at: str
    reason: str


def _internal_player_id(entity_id: str) -> str:
    digest = hashlib.sha256(f"wikidata:{entity_id}".encode()).hexdigest()[:24]
    return f"player-{digest}"


def _query(params: Mapping[str, str]) -> Mapping[str, object]:
    request = Request(
        f"{WIKIDATA_ACTION_API}?{urlencode(params)}",
        headers={"User-Agent": WIKIDATA_USER_AGENT},
    )
    with urlopen(request, timeout=15) as response:  # noqa: S310 - fixed documented endpoint
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise DataValidationError("Wikidata returned an invalid response")
    return payload


def _claim_strings(entity: Mapping[str, object], property_id: str) -> tuple[str, ...]:
    claims = entity.get("claims")
    if not isinstance(claims, dict):
        return ()
    raw_claims = claims.get(property_id)
    if not isinstance(raw_claims, list):
        return ()
    values: list[str] = []
    for claim in raw_claims:
        if not isinstance(claim, dict):
            continue
        mainsnak = claim.get("mainsnak")
        if not isinstance(mainsnak, dict):
            continue
        datavalue = mainsnak.get("datavalue")
        if not isinstance(datavalue, dict):
            continue
        value = datavalue.get("value")
        if isinstance(value, str):
            values.append(value)
    return tuple(sorted(set(values)))


def discover_wikidata_candidate(
    record: SleeperCatalogRecord,
    *,
    query: Callable[[Mapping[str, str]], Mapping[str, object]] = _query,
    retrieved_at: str | None = None,
) -> SleeperExternalIdentityCandidate | None:
    """Return one review-only candidate, never an accepted mapping."""
    if (
        record.position == "DEF"
        or not record.display_name
        or record.position not in SUPPORTED_POSITIONS
    ):
        return None
    search = query(
        {
            "action": "wbsearchentities",
            "search": record.display_name,
            "language": "en",
            "format": "json",
            "limit": "10",
            "origin": "*",
        }
    )
    raw_results = search.get("search")
    if not isinstance(raw_results, list):
        raise DataValidationError("Wikidata search response lacks results")
    ids = tuple(
        item["id"]
        for item in raw_results
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("label") == record.display_name
    )
    if not ids:
        return None
    entities_response = query(
        {
            "action": "wbgetentities",
            "ids": "|".join(ids),
            "props": "claims|labels|info",
            "languages": "en",
            "format": "json",
            "origin": "*",
        }
    )
    raw_entities = entities_response.get("entities")
    if not isinstance(raw_entities, dict):
        raise DataValidationError("Wikidata entity response lacks entities")
    candidates: list[tuple[str, Mapping[str, object], tuple[str, ...], tuple[str, ...]]] = []
    for entity_id in ids:
        entity = raw_entities.get(entity_id)
        if not isinstance(entity, dict):
            continue
        espn_ids = _claim_strings(entity, "P3686")
        nfl_ids = tuple(
            sorted({*_claim_strings(entity, "P9338"), *_claim_strings(entity, "P3539")})
        )
        if espn_ids or nfl_ids:
            candidates.append((entity_id, entity, espn_ids, nfl_ids))
    if len(candidates) != 1:
        return None
    entity_id, entity, espn_ids, nfl_ids = candidates[0]
    labels = entity.get("labels")
    label = None
    if isinstance(labels, dict) and isinstance(labels.get("en"), dict):
        label = labels["en"].get("value")
    if not isinstance(label, str) or not label:
        return None
    revision = entity.get("lastrevid")
    if revision is not None and not isinstance(revision, int):
        raise DataValidationError("Wikidata entity revision is invalid")
    return SleeperExternalIdentityCandidate(
        external_id=record.external_id,
        internal_player_id=_internal_player_id(entity_id),
        position=record.position,
        nfl_team=record.nfl_team,
        wikidata_entity_id=entity_id,
        espn_id=espn_ids[0] if len(espn_ids) == 1 else None,
        nfl_com_id=nfl_ids[0] if len(nfl_ids) == 1 else None,
        provider_display_name=record.display_name,
        candidate_label=label,
        source_retrieved_at=retrieved_at or datetime.now(UTC).isoformat(),
        entity_revision=revision,
    )


def approve_external_identity_candidates(
    candidates: Iterable[SleeperExternalIdentityCandidate],
    decisions: Iterable[SleeperExternalIdentityDecision],
    catalog: Iterable[SleeperCatalogRecord],
    *,
    source_manifest_id: str,
) -> tuple[SleeperExternalObservedIdentity, ...]:
    """Convert exact human decisions into narrow observation-only identities."""
    if not source_manifest_id:
        raise DataValidationError("external identity approval requires catalog provenance")
    candidate_rows = tuple(candidates)
    candidates_by_external = {candidate.external_id: candidate for candidate in candidate_rows}
    if len(candidates_by_external) != len(candidate_rows):
        raise DataValidationError("external identity candidates contain duplicate references")
    catalog_by_external = {record.external_id: record for record in catalog}
    approved: list[SleeperExternalObservedIdentity] = []
    seen: set[str] = set()
    for decision in decisions:
        if not decision.reviewer or not decision.reviewed_at or not decision.reason:
            raise DataValidationError(
                "external identity decisions require reviewer, timestamp, and reason"
            )
        if decision.external_id in seen:
            raise DataValidationError("duplicate external identity decision")
        seen.add(decision.external_id)
        candidate = candidates_by_external.get(decision.external_id)
        record = catalog_by_external.get(decision.external_id)
        if (
            candidate is None
            or record is None
            or candidate.internal_player_id != decision.internal_player_id
        ):
            raise DataValidationError(
                "external identity decision must match a queued candidate exactly"
            )
        if (
            record.position == "DEF"
            or record.position != candidate.position
            or record.nfl_team != candidate.nfl_team
        ):
            raise DataValidationError(
                "external identity candidate conflicts with Sleeper position or team"
            )
        if record.gsis_id or record.espn_id:
            raise DataValidationError(
                "external identity route is only for references without catalog IDs"
            )
        if not re.fullmatch(r"Q[1-9][0-9]*", candidate.wikidata_entity_id):
            raise DataValidationError(
                "external identity candidate has an invalid Wikidata entity ID"
            )
        if not candidate.espn_id and not candidate.nfl_com_id:
            raise DataValidationError("external identity candidate lacks a stable NFL identifier")
        mapping = IdentityMapping(
            provider="sleeper",
            external_id=candidate.external_id,
            internal_player_id=candidate.internal_player_id,
            method="sleeper_reviewed_wikidata_identity_v1",
            provenance=(
                f"wikidata:{candidate.wikidata_entity_id}:revision:{candidate.entity_revision}:"
                f"sleeper_catalog:{source_manifest_id}:reviewer:{decision.reviewer}:"
                f"reviewed_at:{decision.reviewed_at}"
            ),
            asset_type="player",
        )
        approved.append(
            SleeperExternalObservedIdentity(mapping, candidate.position, candidate.nfl_team)
        )
    return tuple(sorted(approved, key=lambda item: item.mapping.external_id))


def _candidate_payload(candidate: SleeperExternalIdentityCandidate) -> dict[str, object]:
    return {
        "external_id": candidate.external_id,
        "internal_player_id": candidate.internal_player_id,
        "position": candidate.position,
        "nfl_team": candidate.nfl_team,
        "wikidata_entity_id": candidate.wikidata_entity_id,
        "espn_id": candidate.espn_id,
        "nfl_com_id": candidate.nfl_com_id,
        "provider_display_name": candidate.provider_display_name,
        "candidate_label": candidate.candidate_label,
        "source_retrieved_at": candidate.source_retrieved_at,
        "entity_revision": candidate.entity_revision,
    }


def write_external_identity_candidates(
    candidates: Iterable[SleeperExternalIdentityCandidate], path: Path, *, source_manifest_id: str
) -> str:
    payload = {
        "schema_version": "1",
        "source": "wikidata",
        "source_manifest_id": source_manifest_id,
        "candidates": [_candidate_payload(candidate) for candidate in candidates],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return hashlib.sha256(serialized.encode()).hexdigest()


def load_external_identity_candidates(
    path: Path,
) -> tuple[str, tuple[SleeperExternalIdentityCandidate, ...]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DataValidationError("external identity candidate file is invalid") from error
    if not isinstance(payload, dict) or payload.get("schema_version") != "1":
        raise DataValidationError("external identity candidate file has an unsupported schema")
    source_manifest_id = payload.get("source_manifest_id")
    rows = payload.get("candidates")
    if not isinstance(source_manifest_id, str) or not isinstance(rows, list):
        raise DataValidationError("external identity candidate file is incomplete")
    try:
        candidates = tuple(SleeperExternalIdentityCandidate(**row) for row in rows)
    except TypeError as error:
        raise DataValidationError("external identity candidate row is invalid") from error
    return source_manifest_id, candidates


def write_external_identity_decisions(
    decisions: Iterable[SleeperExternalIdentityDecision], path: Path
) -> str:
    serialized = (
        json.dumps(
            {"schema_version": "1", "decisions": [asdict(decision) for decision in decisions]},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialized, encoding="utf-8")
    return hashlib.sha256(serialized.encode()).hexdigest()


def load_external_identity_decisions(path: Path) -> tuple[SleeperExternalIdentityDecision, ...]:
    if not path.exists():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DataValidationError("external identity decision file is invalid") from error
    rows = payload.get("decisions") if isinstance(payload, dict) else None
    if payload.get("schema_version") != "1" or not isinstance(rows, list):
        raise DataValidationError("external identity decision file is incomplete")
    try:
        return tuple(SleeperExternalIdentityDecision(**row) for row in rows)
    except TypeError as error:
        raise DataValidationError("external identity decision row is invalid") from error
