"""Validated staging and atomic promotion of immutable prepared datasets."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from .errors import DataValidationError, PublicationError


@dataclass(frozen=True, slots=True)
class OutputFile:
    relative_path: str
    checksum_sha256: str
    row_count: int


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_version: str
    feature_version: str
    transform_revision: str
    source_manifest_ids: tuple[str, ...]
    schemas: Mapping[str, str]
    outputs: tuple[OutputFile, ...]
    validation: Mapping[str, bool]
    license_notes: tuple[str, ...]
    built_at: str


@dataclass(frozen=True, slots=True)
class PinnedDataset:
    draft_id: str
    dataset_version: str
    feature_version: str

    def require_same_version(self, dataset_version: str, feature_version: str) -> None:
        if (self.dataset_version, self.feature_version) != (dataset_version, feature_version):
            raise PublicationError(
                "a draft cannot silently switch its pinned dataset or feature version"
            )


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


class DatasetPublisher:
    """Publishes only fully validated staging directories and retains the old active version."""

    REQUIRED_CHECKS = frozenset(
        {
            "schema",
            "identity",
            "coverage",
            "missingness",
            "leakage",
            "determinism",
            "lineage",
            "timestamps",
            "license",
        }
    )

    def __init__(self, root: Path) -> None:
        self._root = root
        self._versions = root / "versions"
        self._staging = root / ".staging"
        self._active = root / "active.json"

    def stage(
        self,
        manifest: DatasetManifest,
        files: Mapping[str, bytes],
        row_counts: Mapping[str, int],
    ) -> Path:
        self._validate_manifest(manifest)
        staging = self._staging / manifest.dataset_version
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        actual_outputs: list[OutputFile] = []
        try:
            for relative_path, payload in sorted(files.items()):
                if not relative_path.endswith(".parquet"):
                    raise DataValidationError("published outputs must be Parquet files")
                destination = staging / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                _atomic_write(destination, payload)
                actual_outputs.append(
                    OutputFile(
                        relative_path=relative_path,
                        checksum_sha256=hashlib.sha256(payload).hexdigest(),
                        row_count=row_counts[relative_path],
                    )
                )
            declared = tuple(sorted(manifest.outputs, key=lambda output: output.relative_path))
            actual = tuple(sorted(actual_outputs, key=lambda output: output.relative_path))
            if declared != actual:
                raise DataValidationError(
                    "declared output checksums or row counts do not match staging"
                )
            _atomic_write(staging / "dataset_manifest.json", _canonical_json(asdict(manifest)))
            return staging
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def publish(
        self, manifest: DatasetManifest, files: Mapping[str, bytes], row_counts: Mapping[str, int]
    ) -> Path:
        staging = self.stage(manifest, files, row_counts)
        version = self._versions / manifest.dataset_version
        if version.exists():
            if self._read_manifest(version) != manifest:
                raise PublicationError("dataset version already exists with different provenance")
            shutil.rmtree(staging)
            return version
        self._versions.mkdir(parents=True, exist_ok=True)
        staging.replace(version)
        self._root.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            self._active,
            _canonical_json(
                {
                    "dataset_version": manifest.dataset_version,
                    "feature_version": manifest.feature_version,
                }
            ),
        )
        return version

    def active_version(self) -> tuple[str, str] | None:
        if not self._active.exists():
            return None
        value = json.loads(self._active.read_text(encoding="utf-8"))
        return str(value["dataset_version"]), str(value["feature_version"])

    @classmethod
    def _validate_manifest(cls, manifest: DatasetManifest) -> None:
        passed = {name for name, outcome in manifest.validation.items() if outcome}
        failed = cls.REQUIRED_CHECKS - passed
        if failed:
            raise DataValidationError(f"dataset cannot publish; failed checks: {sorted(failed)}")
        if not manifest.source_manifest_ids or not manifest.outputs or not manifest.license_notes:
            raise DataValidationError(
                "manifest requires source lineage, outputs, and license notes"
            )
        if not manifest.built_at or datetime.fromisoformat(manifest.built_at).tzinfo is None:
            raise DataValidationError("manifest requires a timezone-aware build timestamp")

    @staticmethod
    def _read_manifest(version: Path) -> DatasetManifest:
        value = json.loads((version / "dataset_manifest.json").read_text(encoding="utf-8"))
        value["source_manifest_ids"] = tuple(value["source_manifest_ids"])
        value["license_notes"] = tuple(value["license_notes"])
        value["outputs"] = tuple(OutputFile(**output) for output in value["outputs"])
        return DatasetManifest(**value)


def dataset_manifest(
    dataset_version: str,
    feature_version: str,
    transform_revision: str,
    source_manifest_ids: tuple[str, ...],
    schemas: Mapping[str, str],
    outputs: tuple[OutputFile, ...],
    validation: Mapping[str, bool],
    license_notes: tuple[str, ...],
) -> DatasetManifest:
    return DatasetManifest(
        dataset_version=dataset_version,
        feature_version=feature_version,
        transform_revision=transform_revision,
        source_manifest_ids=source_manifest_ids,
        schemas=schemas,
        outputs=outputs,
        validation=validation,
        license_notes=license_notes,
        built_at=datetime.now(UTC).isoformat(),
    )
