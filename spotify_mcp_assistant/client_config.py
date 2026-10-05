"""Client-specific configuration transforms; file commits are kept separate."""

import copy
import json
from collections.abc import MutableMapping
from pathlib import Path

import tomlkit

from spotify_mcp_assistant.setup_types import ClientName, LaunchSpec, MergeResult, SetupError

CLIENTS: tuple[ClientName, ...] = ("claude-desktop", "claude-code", "codex", "cursor")


def client_path(client: ClientName, home: Path, codex_home: str | None) -> Path:
    if client == "codex":
        if codex_home is not None:
            directory = Path(codex_home).expanduser()
            if not codex_home.strip() or not directory.is_absolute() or not directory.is_dir():
                raise SetupError("invalid_codex_home", "CODEX_HOME must be an existing absolute directory.")
        else:
            directory = home / ".codex"
        return directory / "config.toml"
    locations = {
        "claude-desktop": "Library/Application Support/Claude/claude_desktop_config.json",
        "claude-code": ".claude.json",
        "cursor": ".cursor/mcp.json",
    }
    return home / locations[client]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _known_command(entry, command: str) -> bool:
    previous = entry.get("command")
    if not isinstance(previous, str):
        return False
    if previous == command or Path(previous).name == "spotify-mcp-assistant":
        return True
    args = entry.get("args", [])
    return (
        Path(previous).name.startswith("python")
        and isinstance(args, list)
        and args == ["-m", "spotify_mcp_assistant.server"]
    )


def merge_client_config(client: ClientName, text: str | None, launch: LaunchSpec, *, replace_conflict: bool = False) -> MergeResult:
    if not Path(launch.command).is_absolute() or not launch.config_dir.is_absolute():
        raise SetupError("invalid_launch", "Launch and private directory paths must be absolute.")
    try:
        document = tomlkit.parse(text or "") if client == "codex" else json.loads(text if text is not None else "{}", object_pairs_hook=_unique_object)
        if not isinstance(document, MutableMapping):
            raise ValueError("Expected object")
        before = copy.deepcopy(document)
        key = "mcp_servers" if client == "codex" else "mcpServers"
        if key not in document:
            document[key] = {}
        servers = document[key]
        if not isinstance(servers, MutableMapping):
            raise ValueError("Expected servers object")
        entry = servers.get("spotify", {})
        if not isinstance(entry, MutableMapping) or not isinstance(entry.get("env", {}), MutableMapping):
            raise ValueError("Expected entry and env objects")
        conflict = bool(entry) and (
            "url" in entry or entry.get("type", "stdio") != "stdio" or not _known_command(entry, launch.command)
        )
        if conflict and not replace_conflict:
            return MergeResult(text or "", False, True)
        if "spotify" not in servers:
            servers["spotify"] = {}
        entry = servers["spotify"]
        for incompatible in ("url", "auth", "oauth", "headers", "http_headers", "bearer_token_env_var", "envFile", "env_file", "cwd"):
            entry.pop(incompatible, None)
        entry["command"] = launch.command
        entry["args"] = list(launch.args)
        if client == "cursor" or "type" in entry:
            entry["type"] = "stdio"
        if "env" not in entry:
            entry["env"] = {}
        for credential in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI"):
            entry["env"].pop(credential, None)
        entry["env"]["SPOTIFY_CONFIG_DIR"] = str(launch.config_dir)
        changed = document != before
        rendered = tomlkit.dumps(document) if client == "codex" else json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        return MergeResult(rendered if changed else text or rendered, changed)
    except (ValueError, TypeError, KeyError, tomlkit.exceptions.TOMLKitError):
        raise SetupError("invalid_client_config", "Client configuration is malformed or has an unsupported structure.") from None
