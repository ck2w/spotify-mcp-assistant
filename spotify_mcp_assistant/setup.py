"""macOS multi-client setup. Run explicitly; never part of MCP server startup."""

import argparse
import getpass
import os
import shutil
import sys
import warnings
from collections.abc import Callable, Sequence
from importlib.metadata import version
from pathlib import Path

from spotify_mcp_assistant.client_config import (
    CLIENTS,
    client_path,
    commit_target,
    prepare_target,
)
from spotify_mcp_assistant.diagnostics import verify_launch
from spotify_mcp_assistant.installation import ensure_installation
from spotify_mcp_assistant.setup_auth import prepare_authorization
from spotify_mcp_assistant.setup_types import ClientResult, SetupError

RECOVERY = {
    "forbidden": "Check your Spotify application's user allowlist, scopes and account access.",
    "rate_limited": "Wait before retrying; Spotify may have exhausted the shared development quota.",
    "network_error": "Check your connection and rerun setup; existing authorization was retained.",
    "authorization_timeout": "Complete the browser login within two minutes and rerun setup.",
    "authorization_failed": "Check the credentials, consent and callback port 8888; then rerun setup.",
    "auth_busy": "Another client is authorizing or refreshing; wait and retry.",
    "insufficient_scope": "Authorize again to grant all requested Spotify permissions.",
    "client_config_changed": "Another program changed the configuration; rerun setup with other settings editors closed.",
    "client_config_write_failed": "Check directory permissions. Existing content and any listed backup are retained.",
    "stdio_timeout": "The installed MCP did not respond in time; rerun setup after checking the installation.",
    "stdio_failed": "The installed MCP could not start. Repair the uv tool installation and rerun setup.",
    "tool_set_mismatch": "The installed package exposes an unexpected tool set; check its version.",
}


def _input(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise SetupError(
            "interaction_required",
            "Run setup in an interactive terminal to choose clients or enter credentials.",
        )
    return input(prompt)


def _secret(prompt: str) -> str:
    if not sys.stdin.isatty():
        raise SetupError(
            "interaction_required",
            "Run setup in an interactive terminal to enter credentials securely.",
        )
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(prompt)
        except getpass.GetPassWarning:
            raise SetupError(
                "interaction_required",
                "A secure terminal is required to enter the secret; input was not requested with echo enabled.",
            ) from None


def _choose(ask: Callable[[str], str]) -> list[str]:
    print("Choose clients (comma-separated numbers, or 'all'):")
    for number, client in enumerate(CLIENTS, 1):
        print(f"  {number}. {client}")
    choice = ask("Clients: ").strip().lower()
    if choice == "all":
        return list(CLIENTS)
    try:
        selected = [
            CLIENTS[int(item.strip()) - 1]
            for item in choice.split(",")
            if item.strip() and 1 <= int(item.strip()) <= 4
        ]
        if not selected or len(selected) != len(
            [item for item in choice.split(",") if item.strip()]
        ):
            raise ValueError()
        return list(dict.fromkeys(selected))
    except (ValueError, IndexError):
        raise SetupError("invalid_selection", "Choose numbers 1–4 or 'all'.") from None


def _report(results: list[ClientResult]) -> None:
    for result in results:
        print(f"{result.client}: {result.status} — {result.path}")
        if result.backup:
            print(f"  Backup: {result.backup}")
        if result.error_code:
            print(
                f"  {result.error_code}: {RECOVERY.get(result.error_code, 'Inspect the configuration format and rerun setup for this client.')}"
            )
        if result.status in {"written", "unchanged"}:
            action = {
                "claude-desktop": "Quit Claude Desktop completely and reopen it; check its tools list.",
                "claude-code": "Start a new Claude Code session and check /mcp.",
                "codex": "Restart Codex or start a new session; check MCP settings or /mcp in the CLI.",
                "cursor": "Reload/restart Cursor and check Tools & MCP settings.",
            }[result.client]
            print("  " + action)
    print(
        "Client-in-app acceptance: NOT RUN. Verify the connection and call a read-only tool in each selected client."
    )
    print(
        "Existing disabled-service and approval settings were retained; enable the server manually if needed."
    )
    print("A project-level 'spotify' entry may override this user-level setup.")


def _detected(client: str, home: Path) -> bool:
    if client == "claude-code":
        return bool(shutil.which("claude"))
    names = {
        "claude-desktop": "Claude.app",
        "codex": "Codex.app",
        "cursor": "Cursor.app",
    }
    return bool(client == "codex" and shutil.which("codex")) or any(
        (base / names[client]).exists()
        for base in (Path("/Applications"), home / "Applications")
    )


def run_setup(
    argv: Sequence[str], *, ask: Callable[[str], str], ask_secret: Callable[[str], str]
) -> int:
    parser = argparse.ArgumentParser(
        description="Install and authorize Spotify MCP for macOS clients."
    )
    parser.add_argument(
        "--client",
        action="append",
        choices=CLIENTS,
        help="Repeat to select multiple clients; omit for interactive selection.",
    )
    parser.add_argument(
        "--config-dir",
        help="Absolute private Spotify directory (shared by selected clients).",
    )
    parser.add_argument(
        "--replace-credentials",
        action="store_true",
        help="Authorize a different app/account for every client sharing this directory.",
    )
    try:
        args = parser.parse_args(list(argv))
    except SystemExit as result:
        return int(result.code)
    try:
        if sys.platform != "darwin":
            raise SetupError(
                "unsupported_platform",
                "This setup wizard currently supports macOS only. Existing manual server installation remains available.",
            )
        clients = list(dict.fromkeys(args.client or _choose(ask)))
        value = (
            args.config_dir
            if args.config_dir is not None
            else os.environ.get("SPOTIFY_CONFIG_DIR")
        )
        directory = (
            Path(value).expanduser()
            if value is not None
            else Path.home() / ".config/spotify-mcp-assistant"
        )
        if (value is not None and not value.strip()) or not directory.is_absolute():
            raise SetupError(
                "invalid_config_dir",
                "The private directory must be an absolute path; ~ is accepted.",
            )
        print(f"Private directory: {directory}")
        package_version = version("spotify-mcp-assistant")
        launch = ensure_installation(directory, version=package_version)
        print(f"Installed version: {launch.version}; executable: {launch.command}")
        targets, results = [], []
        for client in clients:
            if not _detected(client, Path.home()):
                print(
                    f"{client}: application/CLI not detected; configuration can still be prepared."
                )
            try:
                path = client_path(client, Path.home(), os.environ.get("CODEX_HOME"))
                target = prepare_target(client, path, launch)
                if target.status == "conflict":
                    answer = (
                        ask(
                            f"{client}: a different 'spotify' entry exists. Type 'replace' to replace its transport, or Enter to keep: "
                        )
                        .strip()
                        .lower()
                    )
                    if answer == "replace":
                        target = prepare_target(
                            client, path, launch, replace_conflict=True
                        )
                    else:
                        results.append(
                            ClientResult(
                                client, "skipped", path, error_code="config_conflict"
                            )
                        )
                        continue
                if target.status == "invalid":
                    results.append(
                        ClientResult(
                            client, "failed", path, error_code=target.error_code
                        )
                    )
                    if (
                        ask(
                            f"{client}: configuration cannot be updated. Enter to continue with other clients, or 'quit': "
                        )
                        .strip()
                        .lower()
                        == "quit"
                    ):
                        return 2
                    continue
                targets.append(target)
            except SetupError as error:
                # No guessed path is written when a custom Codex home is invalid.
                print(f"{client}: {error.code} — {error}")
                results.append(
                    ClientResult(client, "failed", Path.home(), error_code=error.code)
                )
        if not targets:
            _report(results)
            return 1
        replacement = args.replace_credentials
        if not replacement and (directory / ".env").exists() and sys.stdin.isatty():
            replacement = (
                ask(
                    "Existing private credentials found. Enter to reuse, or type 'replace' to change application/account: "
                )
                .strip()
                .lower()
                == "replace"
            )
        authorization = prepare_authorization(
            directory, ask=ask, ask_secret=ask_secret, replace_credentials=replacement
        )
        print(f"Authorization: {authorization.status}")
        if authorization.status != "passed":
            print(
                f"{authorization.code}: {RECOVERY.get(authorization.code, 'Check credentials and rerun setup. No client configuration was changed.')}"
            )
            results.extend(
                ClientResult(
                    target.client,
                    "skipped",
                    target.path,
                    error_code="authorization_not_verified",
                )
                for target in targets
            )
            _report(results)
            if authorization.code == "interaction_required":
                return 2
            return 1
        discovery = verify_launch(launch)
        print(f"MCP discovery: {discovery.status}")
        if discovery.status != "passed":
            print(
                f"{discovery.code}: {RECOVERY.get(discovery.code, 'Repair the installation and rerun setup.')}"
            )
            results.extend(
                ClientResult(
                    target.client,
                    "skipped",
                    target.path,
                    error_code="discovery_not_verified",
                )
                for target in targets
            )
            _report(results)
            return 1
        print("All 32 MCP tools discovered; no music data was changed by these checks.")
        results.extend(commit_target(target) for target in targets)
        _report(results)
        return (
            0
            if all(result.status in {"written", "unchanged"} for result in results)
            else 1
        )
    except SetupError as error:
        print(f"{error.code}: {error}")
        return (
            2
            if error.code
            in {"interaction_required", "invalid_selection", "invalid_config_dir"}
            else 1
        )
    except (KeyboardInterrupt, EOFError):
        print("Setup cancelled. Rerun the command when ready.")
        return 2
    except (OSError, ValueError):
        print(
            "Setup could not access a required file. Check directory permissions and rerun."
        )
        return 1


def main() -> None:
    sys.exit(run_setup(sys.argv[1:], ask=_input, ask_secret=_secret))


if __name__ == "__main__":
    main()
