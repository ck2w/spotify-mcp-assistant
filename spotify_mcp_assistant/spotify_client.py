import re

import httpx

from spotify_mcp_assistant.oauth import (
    AuthorizationRequiredError,
    InsufficientScopeError,
    get_access_token,
)
from spotify_mcp_assistant.setup_types import LockTimeoutError


class SpotifyError(Exception):
    def __init__(
        self,
        code,
        message,
        next_action,
        retryable=False,
        retry_after_seconds=None,
        *,
        data=None,
    ):
        super().__init__(message)
        self.data = data
        self.error = {
            "code": code,
            "message": message,
            "next_action": next_action,
            "retryable": retryable,
        }
        if retry_after_seconds is not None:
            self.error["retry_after_seconds"] = retry_after_seconds


def check_response(response: httpx.Response) -> None:
    status = response.status_code
    if 200 <= status < 300:
        return

    errors = {
        401: (
            "auth_required",
            "Authorization failed",
            "Run spotify-mcp-auth to authorize again",
        ),
        403: (
            "forbidden",
            "Spotify refused this operation",
            "Check app access, granted scopes, and account requirements",
        ),
        404: (
            "not_found",
            "Spotify resource unavailable",
            "Check the requested resource; refresh device IDs if relevant",
        ),
        429: (
            "rate_limited",
            "Too many requests",
            "Wait before retrying; follow retry_after_seconds if provided",
        ),
    }
    code, message, action = errors.get(
        status,
        (
            "spotify_error",
            f"Spotify returned HTTP {status}",
            "Check the request; retry later if Spotify is temporarily unavailable",
        ),
    )

    retry_after = response.headers.get("Retry-After", "")
    seconds = int(retry_after) if retry_after.isdigit() else None
    raise SpotifyError(
        code,
        message,
        action,
        retryable=status == 429 or 500 <= status < 600,
        retry_after_seconds=seconds if status == 429 else None,
    )


def spotify_request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json: dict | None = None,
    unknown_code: str = "write_result_unknown",
    required_scopes: tuple[str, ...] = (),
) -> httpx.Response:
    """Reads may refresh once. Writes are never replayed after submission."""
    method = method.upper()
    if (
        method not in {"GET", "POST", "PUT", "DELETE"}
        or not path.startswith("/")
        or path.startswith("//")
    ):
        raise ValueError("Expected a supported method and relative Spotify API path")
    for attempt in range(2 if method == "GET" else 1):
        try:
            token_kwargs = {"force_refresh": attempt == 1}
            if required_scopes:
                token_kwargs["required_scopes"] = required_scopes
            token = get_access_token(**token_kwargs)
        except LockTimeoutError:
            raise SpotifyError(
                "auth_busy",
                "Spotify authorization is busy",
                "Wait for authorization or refresh to finish and retry",
                retryable=True,
            ) from None
        except InsufficientScopeError as error:
            raise SpotifyError(
                "insufficient_scope",
                "Missing scopes: " + ", ".join(error.missing_scopes),
                "Run spotify-mcp-auth to grant the required permissions",
            ) from None
        except AuthorizationRequiredError:
            raise SpotifyError(
                "auth_required",
                "Spotify authorization is unavailable",
                "Run spotify-mcp-auth to authorize again",
            ) from None
        except httpx.HTTPStatusError:
            raise SpotifyError(
                "oauth_config_error",
                "Spotify rejected token refresh",
                "Check configuration or run spotify-mcp-auth again",
            ) from None
        except httpx.RequestError:
            raise SpotifyError(
                "network_error",
                "Could not obtain a Spotify access token",
                "Check your connection and retry later",
                retryable=True,
            ) from None
        except (ValueError, OSError, KeyError, TypeError):
            raise SpotifyError(
                "oauth_config_error",
                "Spotify configuration or token cache is invalid",
                "Check configuration and run spotify-mcp-auth again",
            ) from None
        kwargs = {
            "headers": {"Authorization": f"Bearer {token}"},
            "params": params,
            "timeout": 15,
        }
        if json is not None:
            kwargs["json"] = json
        try:
            response = getattr(httpx, method.lower())(
                f"https://api.spotify.com/v1{path}", **kwargs
            )
        except httpx.RequestError:
            if method != "GET":
                raise SpotifyError(
                    unknown_code,
                    "Could not determine whether the write completed",
                    "Read the affected state before deciding whether to retry",
                ) from None
            raise SpotifyError(
                "network_error",
                "Could not read Spotify state",
                "Check your connection and retry later",
                retryable=True,
            ) from None
        if method == "GET" and response.status_code == 401 and attempt == 0:
            continue
        if method != "GET" and response.status_code >= 500:
            raise SpotifyError(
                unknown_code,
                "Spotify could not confirm the write result",
                "Read the affected state before deciding whether to retry",
            )
        check_response(response)
        return response
    raise AssertionError("Unreachable request state")


def spotify_get(path: str, params: dict | None = None) -> httpx.Response:
    return spotify_request("GET", path, params=params)


def list_devices() -> list[dict]:
    from spotify_mcp_assistant.playback import list_devices as devices

    return devices()


def search_tracks(query: str, limit: int = 5) -> list[dict]:
    from spotify_mcp_assistant.catalog import search_tracks as search

    return search(query, limit)


def get_playback_state() -> dict:
    from spotify_mcp_assistant.playback import get_playback_state as state

    return state()


def play_track(track_uri: str, device_id: str, dry_run: bool = True) -> dict:
    from pydantic import TypeAdapter

    from spotify_mcp_assistant.models import TrackURI
    from spotify_mcp_assistant.playback import _play_track, require_device

    if not re.fullmatch(r"^spotify:track:[A-Za-z0-9]{22}$", track_uri):
        raise SpotifyError(
            "invalid_track", "Invalid track URI", "Use a URI returned by search_tracks"
        )
    TypeAdapter(TrackURI).validate_python(track_uri)
    return _play_track(
        track_uri, require_device(device_id, devices=list_devices()), dry_run
    )
