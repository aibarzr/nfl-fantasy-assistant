import stat
from pathlib import Path

import pytest

from nfl_fantasy_assistant.config import PairingError, TokenStore, credentials_match, generate_token
from nfl_fantasy_assistant.config.settings import load_backend_settings, load_runtime_settings


def test_initial_pairing_uses_private_storage_and_excludes_token_from_backups(
    tmp_path: Path,
) -> None:
    store = TokenStore(tmp_path / "config")

    token = store.initialize()

    assert store.read() == token
    assert len(token) >= 43
    assert store.token_path.stat().st_mode & 0o777 == stat.S_IRUSR | stat.S_IWUSR
    assert store.backup_paths() == ()


def test_mismatch_is_visible_without_echoing_a_secret(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "config")
    token = store.initialize()

    assert credentials_match(token, generate_token()) is False
    with pytest.raises(PairingError, match="No backend token is paired") as error:
        TokenStore(tmp_path / "missing").read()
    assert token not in str(error.value)


def test_rotation_revocation_and_repairing(tmp_path: Path) -> None:
    store = TokenStore(tmp_path / "config")
    initial_token = store.initialize()
    rotated_token = store.rotate()

    assert rotated_token != initial_token
    store.revoke()
    with pytest.raises(PairingError, match="No backend token is paired"):
        store.read()
    assert store.initialize() != rotated_token


def test_non_secret_configuration_is_loopback_only_and_rejects_extra_fields(tmp_path: Path) -> None:
    configuration = tmp_path / "config.toml"
    configuration.write_text('[backend]\nhost = "127.0.0.1"\nport = 8765\n', encoding="utf-8")

    assert load_backend_settings(tmp_path).port == 8765

    configuration.write_text('[backend]\nhost = "0.0.0.0"\nport = 8765\n', encoding="utf-8")
    with pytest.raises(PairingError, match="127.0.0.1"):
        load_backend_settings(tmp_path)

    configuration.write_text(
        '[backend]\nhost = "127.0.0.1"\nport = 8765\ntoken = "not-allowed"\n',
        encoding="utf-8",
    )
    with pytest.raises(PairingError, match="only backend.host and backend.port"):
        load_backend_settings(tmp_path)


def test_runtime_configuration_requires_exact_extension_origin_and_safe_database_name(
    tmp_path: Path,
) -> None:
    (tmp_path / "config.toml").write_text(
        '[backend]\nhost = "127.0.0.1"\nport = 8765\n'
        '[runtime]\nextension_origin = "chrome-extension://abcdefghijklmnop"\n'
        'database_file = "drafts.sqlite3"\n',
        encoding="utf-8",
    )
    assert load_runtime_settings(tmp_path).database_path == tmp_path / "state" / "drafts.sqlite3"
    (tmp_path / "config.toml").write_text(
        '[backend]\nhost = "127.0.0.1"\nport = 8765\n'
        '[runtime]\nextension_origin = "http://bad"\ndatabase_file = "../bad.sqlite3"\n',
        encoding="utf-8",
    )
    with pytest.raises(PairingError, match="extension origin"):
        load_runtime_settings(tmp_path)
