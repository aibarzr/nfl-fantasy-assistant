"""Secret-safe local bearer-token lifecycle for the Phase 0 pairing flow."""

from __future__ import annotations

import hmac
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_DIRECTORY = Path.home() / ".config" / "nfl-fantasy-assistant"
TOKEN_FILE_NAME = "backend.token"
TOKEN_LENGTH = 43


class PairingError(ValueError):
    """A non-secret configuration problem that an operator can act on."""


def generate_token() -> str:
    """Generate a URL-safe 256-bit bearer token using the operating-system CSPRNG."""
    return secrets.token_urlsafe(32)


def _validate_token(token: str) -> str:
    if len(token) < TOKEN_LENGTH or not token.isascii():
        raise PairingError("The paired token is missing or invalid. Pair the extension again.")
    return token


def credentials_match(expected: str, provided: str) -> bool:
    """Compare tokens without exposing either value in a diagnostic."""
    return hmac.compare_digest(_validate_token(expected), _validate_token(provided))


@dataclass(frozen=True, slots=True)
class TokenStore:
    """Stores the backend token in a user-private local configuration directory."""

    config_directory: Path = DEFAULT_CONFIG_DIRECTORY

    @property
    def token_path(self) -> Path:
        return self.config_directory / TOKEN_FILE_NAME

    def _ensure_private_directory(self) -> None:
        self.config_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.config_directory.chmod(0o700)

    def read(self) -> str:
        try:
            token = self.token_path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as error:
            raise PairingError(
                "No backend token is paired. Run the pairing command first."
            ) from error
        return _validate_token(token)

    def initialize(self) -> str:
        if self.token_path.exists():
            raise PairingError("A backend token is already paired. Rotate or revoke it explicitly.")
        return self._replace(generate_token())

    def rotate(self) -> str:
        return self._replace(generate_token())

    def revoke(self) -> None:
        try:
            self.token_path.unlink()
        except FileNotFoundError as error:
            raise PairingError(
                "No backend token is paired, so there is nothing to revoke."
            ) from error

    def backup_paths(self) -> tuple[Path, ...]:
        """Return no secret paths: backup/export callers must exclude credentials by default."""
        return ()

    def _replace(self, token: str) -> str:
        self._ensure_private_directory()
        temporary_path = self.token_path.with_suffix(".tmp")
        try:
            descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            temporary_path.unlink()
            descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as token_file:
            token_file.write(f"{token}\n")
        temporary_path.replace(self.token_path)
        self.token_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return token
