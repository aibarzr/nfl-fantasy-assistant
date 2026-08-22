"""Validation for the backend's non-secret local configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .pairing import DEFAULT_CONFIG_DIRECTORY, PairingError

CONFIG_FILE_NAME = "config.toml"


@dataclass(frozen=True, slots=True)
class BackendSettings:
    """Non-secret loopback binding settings for the HTTP adapter."""

    host: str
    port: int


@dataclass(frozen=True, slots=True)
class RuntimeSettings:
    """Validated non-secret settings needed by the loopback HTTP runtime."""

    backend: BackendSettings
    extension_origin: str
    database_path: Path


def load_backend_settings(config_directory: Path = DEFAULT_CONFIG_DIRECTORY) -> BackendSettings:
    """Load one intentionally narrow, non-secret configuration document."""
    config_path = config_directory / CONFIG_FILE_NAME
    try:
        raw_configuration = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PairingError(
            "No backend configuration is available. Copy config.example.toml to the private "
            "configuration directory."
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise PairingError("Backend configuration is invalid. Check config.toml syntax.") from error

    backend = raw_configuration.get("backend")
    if not isinstance(backend, dict) or set(backend) != {"host", "port"}:
        raise PairingError("Backend configuration must contain only backend.host and backend.port.")

    host = backend["host"]
    port = backend["port"]
    if host != "127.0.0.1":
        raise PairingError("Backend host must be 127.0.0.1.")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise PairingError("Backend port must be an integer from 1 through 65535.")
    return BackendSettings(host=host, port=port)


def load_runtime_settings(config_directory: Path = DEFAULT_CONFIG_DIRECTORY) -> RuntimeSettings:
    """Load runtime-only configuration without allowing arbitrary filesystem paths."""
    backend = load_backend_settings(config_directory)
    raw_configuration = tomllib.loads(
        (config_directory / CONFIG_FILE_NAME).read_text(encoding="utf-8")
    )
    runtime = raw_configuration.get("runtime")
    if not isinstance(runtime, dict) or set(runtime) != {"extension_origin", "database_file"}:
        raise PairingError(
            "Runtime configuration must contain only runtime.extension_origin and "
            "runtime.database_file."
        )
    origin = runtime["extension_origin"]
    database_file = runtime["database_file"]
    if not isinstance(origin, str) or not origin.startswith("chrome-extension://"):
        raise PairingError("Runtime extension origin must be an exact chrome-extension origin.")
    if (
        not isinstance(database_file, str)
        or Path(database_file).name != database_file
        or not database_file.endswith(".sqlite3")
    ):
        raise PairingError("Runtime database_file must be one local .sqlite3 filename.")
    return RuntimeSettings(backend, origin, config_directory / "state" / database_file)
