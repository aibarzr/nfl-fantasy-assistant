"""Immutable local source snapshots fetched through an injectable boundary."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

import nflreadpy as nfl  # type: ignore[import-untyped]

from .errors import DataValidationError


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """Approved source metadata that becomes part of every source manifest."""

    name: str
    season: int
    dataset: str
    license_note: str
    consumed_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RetrievedSource:
    """A complete source payload and its resolved retrieval provenance."""

    payload: bytes
    resolved_url: str
    source_version: str
    schema: dict[str, str]
    retrieved_at: datetime


class SourceFetcher(Protocol):
    def fetch(self, spec: SourceSpec, cache_dir: Path) -> RetrievedSource: ...


@dataclass(frozen=True, slots=True)
class SourceManifest:
    manifest_id: str
    source: str
    season: int
    dataset: str
    resolved_url: str
    source_version: str
    checksum_sha256: str
    schema: dict[str, str]
    license_note: str
    consumed_columns: tuple[str, ...]
    retrieved_at: str
    snapshot_file: str


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


class SnapshotIngestor:
    """Persists a raw payload before writing a complete immutable manifest."""

    def __init__(self, raw_dir: Path, cache_dir: Path) -> None:
        self._raw_dir = raw_dir
        self._cache_dir = cache_dir

    def ingest(self, spec: SourceSpec, fetcher: SourceFetcher) -> SourceManifest:
        retrieved = fetcher.fetch(spec, self._cache_dir)
        if not retrieved.payload:
            raise DataValidationError("retrieval returned an empty payload")
        if retrieved.retrieved_at.tzinfo is None:
            raise DataValidationError("retrieval timestamp must include a timezone")
        checksum = _sha256(retrieved.payload)
        identity_fields = {
            "source": spec.name,
            "season": spec.season,
            "dataset": spec.dataset,
            "resolved_url": retrieved.resolved_url,
            "source_version": retrieved.source_version,
            "checksum_sha256": checksum,
            "schema": retrieved.schema,
            "license_note": spec.license_note,
            "consumed_columns": spec.consumed_columns,
        }
        manifest_id = _sha256(_canonical_json(identity_fields))
        destination = self._raw_dir / spec.name / str(spec.season) / manifest_id
        snapshot_file = destination / "snapshot.parquet"
        manifest_file = destination / "manifest.json"
        if manifest_file.exists() and snapshot_file.exists():
            return self._read_manifest(manifest_file)

        # A source only becomes visible after its payload is durable and its manifest is complete.
        _atomic_write(snapshot_file, retrieved.payload)
        manifest = SourceManifest(
            manifest_id=manifest_id,
            source=spec.name,
            season=spec.season,
            dataset=spec.dataset,
            resolved_url=retrieved.resolved_url,
            source_version=retrieved.source_version,
            checksum_sha256=checksum,
            schema=dict(sorted(retrieved.schema.items())),
            license_note=spec.license_note,
            consumed_columns=tuple(sorted(spec.consumed_columns)),
            retrieved_at=retrieved.retrieved_at.astimezone(UTC).isoformat(),
            snapshot_file=str(snapshot_file.relative_to(self._raw_dir)),
        )
        _atomic_write(manifest_file, _canonical_json(asdict(manifest)))
        return manifest

    @staticmethod
    def _read_manifest(path: Path) -> SourceManifest:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["consumed_columns"] = tuple(value["consumed_columns"])
        return SourceManifest(**value)


class NflreadpyFetcher:
    """Production fetcher for the explicitly approved nflreadpy datasets.

    Dataframes are serialized to local Parquet at this outer adapter boundary;
    no Polars/nflverse object leaves this module.
    """

    _LOADERS: dict[str, Any] = {
        "players": nfl.load_players,
        "player_stats": nfl.load_player_stats,
        "team_stats": nfl.load_team_stats,
        "pbp": nfl.load_pbp,
        "rosters": nfl.load_rosters,
        "snap_counts": nfl.load_snap_counts,
        "depth_charts": nfl.load_depth_charts,
    }

    def fetch(self, spec: SourceSpec, cache_dir: Path) -> RetrievedSource:
        loader = self._LOADERS.get(spec.dataset)
        if loader is None:
            raise DataValidationError(f"unsupported nflreadpy dataset: {spec.dataset}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        frame = loader() if spec.dataset == "players" else loader(spec.season)
        buffer = BytesIO()
        frame.write_parquet(buffer, compression="zstd")
        schema = {name: str(dtype) for name, dtype in frame.schema.items()}
        return RetrievedSource(
            payload=buffer.getvalue(),
            resolved_url=f"nflreadpy:{spec.dataset}:{spec.season}",
            source_version="nflreadpy-local-resolution",
            schema=schema,
            retrieved_at=datetime.now(UTC),
        )
