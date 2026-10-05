"""Explicit offline acceptance check for both installed stdio entry points."""

import argparse
import asyncio
import os
import tempfile
from pathlib import Path


from spotify_mcp_assistant.diagnostics import check_stdio
from spotify_mcp_assistant.setup_types import LaunchSpec


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
            result = await check_stdio(LaunchSpec(command, tuple(args), Path(config), "installed"), cwd=cwd)
            assert result.status == "passed", result.code
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
