import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
from dotenv import dotenv_values

from spotify_mcp_assistant.private_files import atomic_private_write, token_lock

REQUESTED_SCOPES = (
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
    "user-library-read",
    "user-library-modify",
)


class InsufficientScopeError(ValueError):
    def __init__(self, missing_scopes: tuple[str, ...]):
        self.missing_scopes = missing_scopes
        super().__init__("Missing scopes: " + ", ".join(missing_scopes))


def check_scopes(token: dict, required_scopes: tuple[str, ...]) -> None:
    granted = token.get("scope")
    if granted is None:
        return  # Old cache: let the API determine access.
    if not isinstance(granted, str):
        raise ValueError("Invalid scope metadata")
    missing = tuple(scope for scope in required_scopes if scope not in granted.split())
    if missing:
        raise InsufficientScopeError(missing)


class AuthorizationRequiredError(ValueError):
    pass


def get_config_dir() -> Path:
    value = os.environ.get("SPOTIFY_CONFIG_DIR")
    if value is None:
        return Path.home() / ".config" / "spotify-mcp-assistant"

    directory = Path(value).expanduser()
    if not value.strip() or not directory.is_absolute():
        raise ValueError("SPOTIFY_CONFIG_DIR must be an absolute directory path")
    return directory


def load_config(env_file: Path) -> dict[str, str]:
    """Load Spotify configuration and reject missing values."""

    values = dotenv_values(env_file, interpolate=False)

    names = [
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_REDIRECT_URI",
    ]

    config = {name: values.get(name, os.environ.get(name, "")) or "" for name in names}
    missing = [name for name, value in config.items() if not value.strip()]

    if missing:
        raise ValueError(f"Missing configuration: {', '.join(missing)}")

    return config


def build_authorization_url(config: dict[str, str]) -> tuple[str, str]:
    state = secrets.token_urlsafe(32)

    params = {
        "client_id": config["SPOTIFY_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": config["SPOTIFY_REDIRECT_URI"],
        "scope": " ".join(REQUESTED_SCOPES),
        "state": state,
    }

    url = "https://accounts.spotify.com/authorize?" + urlencode(params)
    return url, state


def receive_authorization_code(url: str, state: str) -> str:
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            request = urlsplit(self.path)
            if request.path != "/callback":
                self.send_error(404)
                return

            params = parse_qs(request.query)
            returned_state = params.get("state", [""])[0]
            code = params.get("code", [""])[0]

            if returned_state != state:
                result["error"] = "Authorization state mismatch"
            elif "error" in params:
                result["error"] = "Spotify authorization was denied"
            elif not code:
                result["error"] = "Authorization code is missing"
            else:
                result["code"] = code

            self.send_response(400 if "error" in result else 200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Return to your terminal to see the result.")

        def log_message(self, format, *args):
            pass  # Avoid logging the URL containing the authorization code.

    with HTTPServer(("127.0.0.1", 8888), CallbackHandler) as server:
        server.timeout = 1
        deadline = time.monotonic() + 120
        print("Waiting for Spotify authorization...")
        print("If the browser does not open, open this URL:", url)
        webbrowser.open(url)

        while not result and time.monotonic() < deadline:
            server.handle_request()

    if not result:
        raise TimeoutError("Authorization timed out; run the program again.")
    if "error" in result:
        raise ValueError(result["error"])
    return result["code"]


def exchange_code(config: dict[str, str], code: str) -> dict:
    response = httpx.post(
        "https://accounts.spotify.com/api/token",
        auth=(
            config["SPOTIFY_CLIENT_ID"],
            config["SPOTIFY_CLIENT_SECRET"],
        ),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config["SPOTIFY_REDIRECT_URI"],
        },
        timeout=15,
    )
    response.raise_for_status()

    token = response.json()
    token["expires_at"] = time.time() + token["expires_in"]
    return token


def save_token(token: dict, path: Path) -> None:
    atomic_private_write(path, json.dumps(token, indent=2).encode())


def get_access_token(
    force_refresh: bool = False,
    *,
    required_scopes: tuple[str, ...] = (),
    rejected_access_token: str | None = None,
) -> str:
    with token_lock(get_config_dir()):
        return _get_access_token(
            force_refresh,
            required_scopes=required_scopes,
            rejected_access_token=rejected_access_token,
        )


def _get_access_token(
    force_refresh: bool,
    *,
    required_scopes: tuple[str, ...],
    rejected_access_token: str | None = None,
) -> str:
    directory = get_config_dir()
    token_path = directory / ".spotify_token.json"

    if not token_path.exists():
        raise AuthorizationRequiredError(
            "auth_required: Run spotify-mcp-auth to authorize."
        )

    with token_path.open(encoding="utf-8") as file:
        token = json.load(file)

    cache_replaced = (
        rejected_access_token is not None
        and token["access_token"] != rejected_access_token
    )
    if (not force_refresh or cache_replaced) and time.time() < token["expires_at"] - 60:
        check_scopes(token, required_scopes)
        return token["access_token"]

    config = load_config(directory / ".env")
    token = refresh_token(config, token)
    save_token(token, token_path)
    check_scopes(token, required_scopes)
    return token["access_token"]


def refresh_token(config: dict[str, str], token: dict) -> dict:
    response = httpx.post(
        "https://accounts.spotify.com/api/token",
        auth=(
            config["SPOTIFY_CLIENT_ID"],
            config["SPOTIFY_CLIENT_SECRET"],
        ),
        data={
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        },
        timeout=15,
    )

    if response.status_code == 400:
        if response.json().get("error") == "invalid_grant":
            raise AuthorizationRequiredError(
                "auth_required: Authorization expired or revoked. "
                "Run spotify-mcp-auth again."
            )

    response.raise_for_status()
    refreshed = response.json()
    refreshed["refresh_token"] = (
        refreshed.get("refresh_token") or token["refresh_token"]
    )
    result = {**token, **refreshed}
    result["expires_at"] = time.time() + refreshed["expires_in"]
    return result


def authorize(config: dict[str, str]) -> dict:
    url, state = build_authorization_url(config)
    code = receive_authorization_code(url, state)
    return exchange_code(config, code)


def main() -> None:
    directory = get_config_dir()
    with token_lock(directory):
        config = load_config(directory / ".env")
        token = authorize(config)
        save_token(token, directory / ".spotify_token.json")

    print("Authorization completed. Token cache saved.")


if __name__ == "__main__":
    main()
