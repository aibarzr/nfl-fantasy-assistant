"""Local review-queue operations for explicit Sleeper identity approvals."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .errors import DataValidationError
from .sleeper_identity import SleeperReviewCandidate, SleeperReviewDecision


@dataclass(frozen=True, slots=True)
class SleeperReviewQueue:
    source_manifest_id: str
    candidates: tuple[SleeperReviewCandidate, ...]
    checksum: str


def _read_json(path: Path) -> tuple[dict[str, object], str]:
    payload = path.read_bytes()
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise DataValidationError("review file must contain JSON") from error
    if not isinstance(value, dict):
        raise DataValidationError("review file must contain a JSON object")
    return value, hashlib.sha256(payload).hexdigest()


def load_review_queue_artifact(path: Path) -> SleeperReviewQueue:
    value, checksum = _read_json(path)
    if value.get("status") != "requires_explicit_review":
        raise DataValidationError("not a Sleeper review queue")
    source_manifest_id = value.get("source_manifest_id")
    rows = value.get("candidates")
    if (
        not isinstance(source_manifest_id, str)
        or not source_manifest_id
        or not isinstance(rows, list)
    ):
        raise DataValidationError("Sleeper review queue is missing provenance or candidates")
    candidates = tuple(
        SleeperReviewCandidate(
            external_id=row["external_id"],
            candidate_internal_player_id=row["candidate_internal_player_id"],
            position=row["position"],
            nfl_team=row.get("nfl_team"),
            provider_display_name=row["provider_display_name"],
            internal_display_name=row["internal_display_name"],
            batch_eligible=bool(row.get("batch_eligible", False)),
        )
        for row in rows
        if isinstance(row, dict)
    )
    if len(candidates) != len(rows) or len({row.external_id for row in candidates}) != len(
        candidates
    ):
        raise DataValidationError("Sleeper review queue contains invalid or duplicate candidates")
    return SleeperReviewQueue(source_manifest_id, candidates, checksum)


def load_review_queue(path: Path) -> tuple[SleeperReviewCandidate, ...]:
    return load_review_queue_artifact(path).candidates


def load_review_decisions(path: Path) -> tuple[SleeperReviewDecision, ...]:
    if not path.exists():
        return ()
    value, _ = _read_json(path)
    rows = value.get("decisions", ())
    if not isinstance(rows, list):
        raise DataValidationError("Sleeper decisions must be a JSON list")
    try:
        return tuple(SleeperReviewDecision(**row) for row in rows)
    except TypeError as error:
        raise DataValidationError("Sleeper decision has an invalid shape") from error


def review_decisions_checksum(path: Path) -> str:
    if not path.exists():
        raise DataValidationError("Sleeper review decisions file does not exist")
    _, checksum = _read_json(path)
    return checksum


def validate_decisions_against_queue(
    queue: SleeperReviewQueue, decisions: Iterable[SleeperReviewDecision]
) -> tuple[SleeperReviewDecision, ...]:
    """Require recorded decisions to target the exact candidate shown to the reviewer."""
    candidates = {candidate.external_id: candidate for candidate in queue.candidates}
    materialized = tuple(decisions)
    if len({decision.external_id for decision in materialized}) != len(materialized):
        raise DataValidationError("Sleeper decisions contain duplicate external IDs")
    for decision in materialized:
        candidate = candidates.get(decision.external_id)
        if (
            candidate is None
            or candidate.candidate_internal_player_id != decision.internal_player_id
        ):
            raise DataValidationError("Sleeper decision does not match its queued candidate")
    return materialized


def write_review_decisions(decisions: Iterable[SleeperReviewDecision], path: Path) -> None:
    rows = [
        {
            "external_id": decision.external_id,
            "internal_player_id": decision.internal_player_id,
            "reviewer": decision.reviewer,
            "reviewed_at": decision.reviewed_at,
            "reason": decision.reason,
        }
        for decision in sorted(decisions, key=lambda decision: decision.external_id)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": "1", "decisions": rows}, indent=2) + "\n")


def next_review_candidate(
    candidates: Iterable[SleeperReviewCandidate], decisions: Iterable[SleeperReviewDecision]
) -> SleeperReviewCandidate | None:
    decided = {decision.external_id for decision in decisions}
    return next(
        (candidate for candidate in candidates if candidate.external_id not in decided), None
    )


def batch_review_candidates(
    candidates: Iterable[SleeperReviewCandidate], decisions: Iterable[SleeperReviewDecision]
) -> tuple[SleeperReviewCandidate, ...]:
    """Return pending candidates safe for a deliberately confirmed batch approval."""
    decided = {decision.external_id for decision in decisions}
    return tuple(
        candidate
        for candidate in candidates
        if candidate.batch_eligible and candidate.external_id not in decided
    )
