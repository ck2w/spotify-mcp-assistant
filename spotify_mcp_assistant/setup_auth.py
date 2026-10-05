"""Interactive authorization without relying on inherited Spotify credentials."""

import io
import json
import os
import re
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import httpx
from dotenv import dotenv_values

from spotify_mcp_assistant import oauth
from spotify_mcp_assistant.private_files import atomic_private_write, token_lock
from spotify_mcp_assistant.setup_types import CheckResult, LockTimeoutError, SetupError

REDIRECT_URI = "http://127.0.0.1:8888/callback"
CONFIG_KEYS = ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI")


def _read(path: Path) -> bytes | None:
    if path.is_symlink():
        raise SetupError(
            "private_file_symlink", "Private configuration must not be a symlink."
        )
    return path.read_bytes() if path.exists() else None


def _ask_value(prompt: str, ask: Callable[[str], str]) -> str:
    while True:
        value = ask(prompt).strip()
        if value and not any(char in value for char in ("\n", "\r", "\x00")):
            return value
        print("Enter a nonempty single-line value.")


def _env_bytes(original: bytes | None, config: dict[str, str]) -> bytes:
    text = (original or b"").decode("utf-8")
    # Known credentials must be single-line; preserve other settings and comments.
    pattern = re.compile(r"^\s*(?:export\s+)?(" + "|".join(CONFIG_KEYS) + r")\s*=")
    lines = [line for line in text.splitlines() if not pattern.match(line)]
    for name in CONFIG_KEYS:
        escaped = config[name].replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"{name}='{escaped}'")
    return ("\n".join(lines) + "\n").encode()


def _commit_pair(
    directory: Path,
    env_bytes: bytes,
    token: dict,
    originals: tuple[bytes | None, bytes | None],
) -> None:
    paths = (directory / ".env", directory / ".spotify_token.json")
    suffix = f".backup-{time.time_ns()}-{uuid.uuid4().hex[:8]}"
    for path, old in zip(paths, originals):
        if old is not None:
            atomic_private_write(path.with_name(path.name + suffix), old)
    try:
        atomic_private_write(paths[0], env_bytes)
        oauth.save_token(token, paths[1])
    except OSError:
        try:
            for path, old in zip(paths, originals):
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic_private_write(path, old)
        except OSError:
            raise SetupError(
                "private_restore_failed",
                "Private files could not be restored. Recover the .backup files in the private directory before retrying.",
            ) from None
        raise SetupError(
            "private_write_failed",
            "Private files could not be saved; previous files were restored.",
        ) from None


def _verify_devices(token: dict) -> None:
    response = httpx.get(
        "https://api.spotify.com/v1/me/player/devices",
        headers={"Authorization": f"Bearer {token['access_token']}"},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("devices"), list):
        raise ValueError("Invalid devices result")


def prepare_authorization(
    directory: Path,
    *,
    ask: Callable[[str], str],
    ask_secret: Callable[[str], str],
    replace_credentials: bool = False,
) -> CheckResult:
    try:
        with token_lock(directory):
            env_path, token_path = directory / ".env", directory / ".spotify_token.json"
            originals = (_read(env_path), _read(token_path))
            values = dotenv_values(
                stream=io.StringIO((originals[0] or b"").decode()), interpolate=False
            )
            config = {name: values.get(name) or "" for name in CONFIG_KEYS}
            if any(os.environ.get(name) for name in CONFIG_KEYS):
                print(
                    "Spotify values in your shell are ignored by setup; the selected private directory supplies credentials."
                )
            if replace_credentials:
                print(
                    "Changing account/application affects every client sharing this directory."
                )
            old_config = dict(config)
            if (
                replace_credentials
                or not config["SPOTIFY_CLIENT_ID"]
                or not config["SPOTIFY_CLIENT_SECRET"]
            ):
                print(
                    "Open https://developer.spotify.com/dashboard and create your own app."
                )
                print(f"Register this exact redirect URI: {REDIRECT_URI}")
                print(
                    "Confirm your account has app access; playback requires Spotify Premium."
                )
                config["SPOTIFY_CLIENT_ID"] = _ask_value("Spotify Client ID: ", ask)
                config["SPOTIFY_CLIENT_SECRET"] = _ask_value(
                    "Spotify Client Secret (hidden): ", ask_secret
                )
            config["SPOTIFY_REDIRECT_URI"] = REDIRECT_URI
            if any(
                any(c in value for c in ("\n", "\r", "\x00"))
                for value in config.values()
            ):
                raise SetupError(
                    "invalid_credentials",
                    "Credentials must be single-line; replace them with setup --replace-credentials.",
                )
            changed = config != old_config or replace_credentials
            token = None
            if not changed and originals[1] is not None:
                try:
                    candidate = json.loads(originals[1])
                    if isinstance(candidate, dict) and isinstance(
                        candidate.get("scope"), str
                    ):
                        oauth.check_scopes(candidate, oauth.REQUESTED_SCOPES)
                        if (
                            candidate.get("access_token")
                            and candidate.get("expires_at", 0) > time.time() + 60
                        ):
                            token = candidate
                        elif candidate.get("refresh_token"):
                            try:
                                token = oauth.refresh_token(config, candidate)
                            except oauth.AuthorizationRequiredError:
                                pass
                except (ValueError, KeyError, TypeError, oauth.InsufficientScopeError):
                    pass
            if token is None:
                print("Authorize your Spotify account in the browser.")
                token = oauth.authorize(config)
            if not isinstance(token.get("scope"), str):
                raise SetupError(
                    "insufficient_scope",
                    "Authorization did not report granted permissions; authorize again.",
                )
            oauth.check_scopes(token, oauth.REQUESTED_SCOPES)
            try:
                _verify_devices(token)
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 401:
                    raise
                print("Spotify rejected the cached authorization; authorize again.")
                token = oauth.authorize(config)
                if not isinstance(token.get("scope"), str):
                    raise SetupError(
                        "insufficient_scope",
                        "Authorization did not report granted permissions; authorize again.",
                    )
                oauth.check_scopes(token, oauth.REQUESTED_SCOPES)
                _verify_devices(token)
            desired = _env_bytes(originals[0], config)
            if originals != (desired, json.dumps(token, indent=2).encode()):
                _commit_pair(directory, desired, token, originals)
            for path in (env_path, token_path):
                path.chmod(0o600)
            print(
                "Spotify authorization verified with a read-only request (device availability and playback are not verified)."
            )
            return CheckResult("passed")
    except LockTimeoutError:
        return CheckResult("failed", "auth_busy")
    except SetupError as error:
        print(str(error))
        return CheckResult("failed", error.code)
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        code = {403: "forbidden", 429: "rate_limited", 401: "auth_required"}.get(
            status, "oauth_rejected"
        )
        return CheckResult("failed", code)
    except httpx.RequestError:
        return CheckResult("failed", "network_error")
    except TimeoutError:
        return CheckResult("failed", "authorization_timeout")
    except (OSError, ValueError, KeyError, TypeError):
        return CheckResult("failed", "authorization_failed")
