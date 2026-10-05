"""Offline MCP discovery against the actual launch command, with bounded output."""

import asyncio
import os
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from spotify_mcp_assistant.setup_types import CheckResult, LaunchSpec

EXPECTED_TOOLS = frozenset({
    "search_tracks", "get_track", "list_playlists", "get_playlist", "get_playlist_tracks",
    "create_playlist", "update_playlist_details", "add_playlist_tracks", "remove_playlist_tracks",
    "replace_playlist_tracks", "reorder_playlist_tracks", "save_playlist", "unsave_playlist",
    "list_devices", "get_playback_state", "play_track", "play_playlist", "transfer_playback",
    "pause_playback", "resume_playback", "next_track", "previous_track", "seek_playback",
    "set_volume", "set_shuffle", "set_repeat", "get_queue", "add_to_queue", "get_saved_tracks",
    "save_tracks", "remove_saved_tracks", "check_saved_tracks",
})


async def _discover(launch: LaunchSpec, cwd: Path) -> CheckResult:
    env = {key: value for key, value in os.environ.items() if not key.startswith("SPOTIFY_") and key not in {"PYTHONPATH", "PYTHONHOME"}}
    env["SPOTIFY_CONFIG_DIR"] = str(launch.config_dir)
    parameters = StdioServerParameters(command=launch.command, args=list(launch.args), cwd=str(cwd), env=env)
    # Suppress raw stderr, which could contain third-party diagnostics or identifiers.
    with open(os.devnull, "w") as errors:
        async with stdio_client(parameters, errlog=errors) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                if len(tools) != 32 or {tool.name for tool in tools} != EXPECTED_TOOLS:
                    return CheckResult("failed", "tool_set_mismatch")
    return CheckResult("passed")


async def check_stdio(launch: LaunchSpec, *, cwd: Path, timeout: float = 30.0) -> CheckResult:
    try:
        return await asyncio.wait_for(_discover(launch, cwd), timeout=timeout)
    except TimeoutError:
        return CheckResult("failed", "stdio_timeout")
    except Exception:
        return CheckResult("failed", "stdio_failed")


def verify_launch(launch: LaunchSpec) -> CheckResult:
    with tempfile.TemporaryDirectory(prefix="spotify-setup-discovery-") as directory:
        return asyncio.run(check_stdio(launch, cwd=Path(directory)))
