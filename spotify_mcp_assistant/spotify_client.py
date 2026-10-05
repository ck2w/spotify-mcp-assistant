import re

import httpx

from spotify_mcp_assistant.oauth import AuthorizationRequiredError, get_access_token


class SpotifyError(Exception):
    def __init__(
        self,
        code,
        message,
        next_action,
        retryable=False,
        retry_after_seconds=None,
    ):
        super().__init__(message)
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


def spotify_get(path: str, params: dict | None = None) -> httpx.Response:
    try:
        for attempt in range(2):
            token = get_access_token(force_refresh=attempt == 1)
            response = httpx.get(
                f"https://api.spotify.com/v1{path}",
                headers={"Authorization": f"Bearer {token}"},
                params=params,
                timeout=15,
            )

            if response.status_code != 401 or attempt == 1:
                break

    except AuthorizationRequiredError:
        raise SpotifyError(
            "auth_required",
            "Spotify authorization is missing, expired, or revoked",
            "Run spotify-mcp-auth to authorize again",
        ) from None

    except httpx.HTTPStatusError as error:
        if error.response.status_code in (400, 401):
            raise SpotifyError(
                "oauth_config_error",
                "Spotify rejected the token refresh request",
                "Check your Spotify app credentials and OAuth configuration",
            ) from None

        check_response(error.response)

    except httpx.TimeoutException:
        raise SpotifyError(
            "network_error",
            "Spotify request timed out",
            "Check your connection and retry later",
            retryable=True,
        ) from None

    except httpx.RequestError:
        raise SpotifyError(
            "network_error",
            "Could not connect to Spotify",
            "Check your connection and retry later",
            retryable=True,
        ) from None

    check_response(response)
    return response


def list_devices() -> list[dict]:
    response = spotify_get("/me/player/devices")

    devices = response.json()["devices"]
    return [
        {
            "device_id": device["id"],
            "name": device["name"],
            "type": device["type"],
            "is_active": device["is_active"],
            "is_restricted": device["is_restricted"],
        }
        for device in devices
    ]


def search_tracks(query: str, limit: int = 5) -> list[dict]:
    query = query.strip()
    if not query:
        raise ValueError("query must not be empty")
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")

    response = spotify_get(
        "/search",
        params={"q": query, "type": "track", "limit": limit},
    )

    tracks = response.json()["tracks"]["items"]
    return [
        {
            "name": track["name"],
            "artists": [artist["name"] for artist in track["artists"]],
            "track_uri": track["uri"],
            "url": track["external_urls"]["spotify"],
        }
        for track in tracks
    ]


def get_playback_state() -> dict:
    response = spotify_get("/me/player")

    if response.status_code == 204:
        return {
            "has_playback": False,
            "is_playing": False,
            "progress_ms": None,
            "track": None,
            "device": None,
        }

    playback = response.json()
    item = playback.get("item")
    device = playback.get("device")

    track = None
    if item and item.get("type") == "track":
        track = {
            "name": item["name"],
            "artists": [artist["name"] for artist in item["artists"]],
            "track_uri": item["uri"],
        }

    return {
        "has_playback": True,
        "is_playing": playback["is_playing"],
        "progress_ms": playback.get("progress_ms"),
        "track": track,
        "device": (
            {
                "device_id": device["id"],
                "name": device["name"],
            }
            if device
            else None
        ),
    }


def play_track(
    track_uri: str,
    device_id: str,
    dry_run: bool = True,
) -> dict:
    if not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", track_uri):
        raise SpotifyError(
            "invalid_track",
            "Invalid track URI",
            "Use a track_uri returned by search_tracks",
        )

    if not device_id.strip():
        raise SpotifyError(
            "device_unavailable",
            "Device ID is required",
            "Call list_devices and select a device",
        )

    device = next(
        (item for item in list_devices() if item["device_id"] == device_id),
        None,
    )
    if device is None:
        raise SpotifyError(
            "device_unavailable",
            "Device is no longer available",
            "Open Spotify and call list_devices again",
        )
    if device["is_restricted"]:
        raise SpotifyError(
            "device_restricted",
            "Device does not allow playback control",
            "Select another device from list_devices",
        )

    if dry_run:
        return {
            "status": "preview",
            "track_uri": track_uri,
            "device_id": device_id,
            "device_name": device["name"],
            "next_action": "Confirm this song and device before playing",
        }

    write_started = False
    try:
        token = get_access_token()
        write_started = True
        response = httpx.put(
            "https://api.spotify.com/v1/me/player/play",
            headers={"Authorization": f"Bearer {token}"},
            params={"device_id": device_id},
            json={"uris": [track_uri]},
            timeout=15,
        )
    except AuthorizationRequiredError:
        raise SpotifyError(
            "auth_required",
            "Spotify authorization is unavailable",
            "Run spotify-mcp-auth to authorize again",
        ) from None
    except httpx.HTTPStatusError as error:
        check_response(error.response)
    except httpx.RequestError:
        if write_started:
            raise SpotifyError(
                "playback_result_unknown",
                "Could not determine whether playback started",
                "Call get_playback_state before attempting playback again",
            ) from None
        raise SpotifyError(
            "network_error",
            "Could not obtain a Spotify access token",
            "Check your connection and retry later",
            retryable=True,
        ) from None

    check_response(response)
    return {
        "status": "submitted",
        "track_uri": track_uri,
        "device_id": device_id,
        "next_action": "Call get_playback_state to verify playback",
    }
