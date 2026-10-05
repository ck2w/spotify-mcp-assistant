"""Locate and prepare the persistent uv tool installation used by GUI clients."""

import shutil
import subprocess
from pathlib import Path

from spotify_mcp_assistant.setup_types import LaunchSpec, SetupError

PACKAGE_NAME = "spotify-mcp-assistant"


def _run(argv: list[str], *, timeout: float = 30) -> str:
    try:
        return subprocess.run(
            argv, check=True, capture_output=True, text=True, timeout=timeout
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise SetupError(
            "installation_failed",
            "uv could not prepare the installation. Check your connection, package version and executable conflicts; no client configuration was changed.",
        ) from None


def _installed_launch(uv: str, directory: Path, version: str) -> LaunchSpec | None:
    root = Path(_run([uv, "tool", "dir"]))
    bin_dir = Path(_run([uv, "tool", "dir", "--bin"]))
    exported = bin_dir / PACKAGE_NAME
    if not exported.exists():
        return None
    command = exported.resolve()
    if not command.is_relative_to(root.resolve()):
        raise SetupError(
            "executable_conflict",
            "A different installation owns the Spotify executable. Resolve it manually; setup will not force an overwrite.",
        )
    python = command.parent / "python"
    if not python.exists():
        return None
    found = _run(
        [
            str(python),
            "-c",
            "from importlib.metadata import version; print(version('spotify-mcp-assistant'))",
        ]
    )
    if found != version:
        return None
    return LaunchSpec(str(command), (), directory, found)


def ensure_installation(
    config_dir: Path, *, version: str, uv_path: Path | None = None
) -> LaunchSpec:
    uv = str(uv_path) if uv_path else shutil.which("uv")
    if not uv:
        raise SetupError(
            "uv_missing",
            "Install uv first: https://docs.astral.sh/uv/getting-started/installation/",
        )
    current = _installed_launch(uv, config_dir, version)
    if current is not None:
        return current
    print(f"Installing Spotify MCP {version} into a persistent uv environment…")
    _run(
        [uv, "tool", "install", "--python", "3.12", f"{PACKAGE_NAME}=={version}"],
        timeout=300,
    )
    installed = _installed_launch(uv, config_dir, version)
    if installed is None:
        raise SetupError(
            "invalid_installation",
            "The installed executable or version could not be verified. Run setup again after repairing the uv tool installation.",
        )
    return installed
