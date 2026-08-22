"""Local pairing, configuration validation, and loopback API entrypoints."""

from __future__ import annotations

import argparse
from pathlib import Path

from nfl_fantasy_assistant.api import create_app
from nfl_fantasy_assistant.config import (
    PairingError,
    TokenStore,
    load_runtime_settings,
)


def main() -> None:
    """Run the narrow local command surface without exposing secrets."""
    parser = argparse.ArgumentParser(description="NFL Fantasy Assistant backend")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate non-secret runtime configuration and local pairing.",
    )
    subparsers = parser.add_subparsers(dest="command")
    pairing_parser = subparsers.add_parser("pair", help="Manage the local backend bearer token.")
    pairing_parser.add_argument("action", choices=("init", "rotate", "revoke"))
    pairing_parser.add_argument(
        "--config-dir",
        type=Path,
        help="Override the private local configuration directory for this command.",
    )
    serve_parser = subparsers.add_parser("serve", help="Run the authenticated loopback API.")
    serve_parser.add_argument("--config-dir", type=Path, help="Private configuration directory.")
    arguments = parser.parse_args()

    if arguments.command == "pair":
        store = TokenStore(arguments.config_dir) if arguments.config_dir else TokenStore()
        try:
            if arguments.action == "init":
                token = store.initialize()
                print("Pairing token (displayed once; do not save it in source or a page):")
                print(token)
            elif arguments.action == "rotate":
                token = store.rotate()
                print("New pairing token (re-pair the extension; displayed once):")
                print(token)
            else:
                store.revoke()
                print(
                    "Backend token revoked. The extension must be paired before authenticated use."
                )
        except PairingError as error:
            parser.error(str(error))
        return

    if arguments.command == "serve":
        try:
            config_directory = arguments.config_dir
            runtime = (
                load_runtime_settings(config_directory)
                if config_directory
                else load_runtime_settings()
            )
            token = TokenStore(config_directory).read() if config_directory else TokenStore().read()
        except PairingError as error:
            parser.error(str(error))
        import uvicorn

        uvicorn.run(
            create_app(runtime.database_path, token, runtime.extension_origin),
            host=runtime.backend.host,
            port=runtime.backend.port,
        )
        return

    if arguments.check_config:
        try:
            settings = load_runtime_settings().backend
            TokenStore().read()
        except PairingError as error:
            parser.error(str(error))
        print(f"Configuration is valid for {settings.host}:{settings.port}.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
