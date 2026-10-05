"""Explicit offline acceptance check for both installed stdio entry points."""

import argparse
import asyncio
import os
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "search_tracks",
    "get_track",
    "list_playlists",
    "get_playlist",
    "get_playlist_tracks",
    "create_playlist",
    "update_playlist_details",
    "add_playlist_tracks",
    "remove_playlist_tracks",
    "replace_playlist_tracks",
    "reorder_playlist_tracks",
    "save_playlist",
    "unsave_playlist",
    "list_devices",
    "get_playback_state",
    "play_track",
    "play_playlist",
    "transfer_playback",
    "pause_playback",
    "resume_playback",
    "next_track",
    "previous_track",
    "seek_playback",
    "set_volume",
    "set_shuffle",
    "set_repeat",
    "get_queue",
    "add_to_queue",
    "get_saved_tracks",
    "save_tracks",
    "remove_saved_tracks",
    "check_saved_tracks",
}


async def check(server_python: Path, cwd: Path):
    with tempfile.TemporaryDirectory(prefix="spotify-stdio-config-") as config:
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("SPOTIFY_")
            and key not in {"PYTHONPATH", "PYTHONHOME"}
        }
        env["SPOTIFY_CONFIG_DIR"] = config
        commands = [
            (str(server_python), ["-m", "spotify_mcp_assistant.server"]),
            (str(server_python.parent / "spotify-mcp-assistant"), []),
        ]
        for command, args in commands:
            async with stdio_client(
                StdioServerParameters(command=command, args=args, cwd=cwd, env=env)
            ) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    tools = (await session.list_tools()).tools
                    assert (
                        len(tools) == 32
                        and {tool.name for tool in tools} == EXPECTED_TOOLS
                    )
                    print(f"PASS: {command} {args}: 32 tools from {cwd}")
        assert not list(Path(config).iterdir()), (
            "Discovery must not create token/config files"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-python", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(check(args.server_python.absolute(), args.cwd.absolute()))
