"""Playlist reads; item positions include unavailable and non-track entries."""

from pydantic import TypeAdapter

from spotify_mcp_assistant import spotify_client as api
from spotify_mcp_assistant.catalog import page, track_detail
from spotify_mcp_assistant.models import Offset, PageLimit, PlaylistID

READ_SCOPES = ("playlist-read-private", "playlist-read-collaborative")
WRITE_SCOPES = ("playlist-modify-private", "playlist-modify-public")


def playlist_summary(data: dict) -> dict:
    contents = data.get("items", data.get("tracks"))
    return {
        "playlist_id": data["id"],
        "playlist_uri": data.get("uri", "spotify:playlist:" + data["id"]),
        "name": data.get("name", ""),
        "url": (data.get("external_urls") or {}).get("spotify", ""),
        "owner_id": (data.get("owner") or {}).get("id"),
        "public": data.get("public"),
        "collaborative": data.get("collaborative"),
        "snapshot_id": data.get("snapshot_id"),
        "total": contents.get("total") if isinstance(contents, dict) else None,
        "contents_accessible": isinstance(contents, dict),
    }


def list_playlists(limit: int = 20, offset: int = 0) -> dict:
    TypeAdapter(PageLimit).validate_python(limit)
    TypeAdapter(Offset).validate_python(offset)
    data = api.spotify_request(
        "GET",
        "/me/playlists",
        params={"limit": limit, "offset": offset},
        required_scopes=READ_SCOPES,
    ).json()
    return page(data, [playlist_summary(item) for item in data["items"]], limit, offset)


def get_playlist(playlist_id: str) -> dict:
    TypeAdapter(PlaylistID).validate_python(playlist_id)
    data = api.spotify_request(
        "GET", "/playlists/" + playlist_id, required_scopes=READ_SCOPES
    ).json()
    return playlist_summary(data)


def get_playlist_tracks(playlist_id: str, limit: int = 20, offset: int = 0) -> dict:
    TypeAdapter(PlaylistID).validate_python(playlist_id)
    TypeAdapter(PageLimit).validate_python(limit)
    TypeAdapter(Offset).validate_python(offset)
    data = api.spotify_request(
        "GET",
        f"/playlists/{playlist_id}/items",
        params={"limit": limit, "offset": offset},
        required_scopes=READ_SCOPES,
    ).json()
    if "items" not in data:
        raise api.SpotifyError(
            "contents_unavailable",
            "Playlist contents are not accessible",
            "Select a playlist you own or collaborate on",
        )
    entries = []
    for index, entry in enumerate(data["items"]):
        entry = entry or {}
        item = entry.get("item", entry.get("track"))
        kind = item.get("type", "unknown") if item else "unavailable"
        entries.append(
            {
                "position": offset + index,
                "added_at": entry.get("added_at"),
                "is_local": bool(entry.get("is_local") or (item or {}).get("is_local")),
                "item_type": kind,
                "track": track_detail(item) if kind == "track" else None,
            }
        )
    return page(data, entries, limit, offset)


from typing import Annotated

from pydantic import Field, StringConstraints

from spotify_mcp_assistant.models import ReplacementURIs, TrackURIs
from spotify_mcp_assistant.mutations import mutation, submit_batches, submit_once


def _precheck(playlist_id, expected_snapshot_id=None):
    current = get_playlist(playlist_id)
    if not current["contents_accessible"]:
        raise api.SpotifyError(
            "contents_unavailable",
            "Playlist contents are not accessible",
            "Select a playlist you own or collaborate on",
        )
    if (
        expected_snapshot_id is not None
        and current["snapshot_id"] != expected_snapshot_id
    ):
        raise api.SpotifyError(
            "conflict",
            "Playlist changed since preview",
            "Read the playlist and preview again",
        )
    return current


def _options(public, collaborative):
    if public is True and collaborative is True:
        raise api.SpotifyError(
            "invalid_playlist_options",
            "Collaborative playlists cannot be public",
            "Set public=false or collaborative=false",
        )


def _snapshot(response):
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
    except ValueError:
        pass
    raise api.SpotifyError(
        "write_result_unknown",
        "Write response did not contain valid result metadata",
        "Read playlist state before deciding whether to retry",
    )


def create_playlist(
    name: str,
    description: str = "",
    public: bool = False,
    collaborative: bool = False,
    dry_run: bool = True,
) -> dict:
    name = TypeAdapter(
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    ).validate_python(name)
    _options(public, collaborative)
    params = {
        "name": name,
        "description": description,
        "public": public,
        "collaborative": collaborative,
    }
    data = mutation("create_playlist", {}, params)
    if dry_run:
        return data
    response = submit_once(
        data,
        lambda: api.spotify_request(
            "POST", "/me/playlists", json=params, required_scopes=WRITE_SCOPES
        ),
    )
    try:
        created = _snapshot(response)
        TypeAdapter(PlaylistID).validate_python(created["id"])
    except (KeyError, ValueError, api.SpotifyError):
        data["status"] = "unknown"
        raise api.SpotifyError(
            "write_result_unknown",
            "Playlist may have been created but its ID is unavailable",
            "List playlists before attempting another creation",
            data=data,
        ) from None
    data.update(
        playlist_id=created["id"],
        playlist_uri=created.get("uri", "spotify:playlist:" + created["id"]),
        url=(created.get("external_urls") or {}).get("spotify"),
    )
    return data


def update_playlist_details(
    playlist_id: str,
    name: str | None = None,
    description: str | None = None,
    public: bool | None = None,
    collaborative: bool | None = None,
    dry_run: bool = True,
) -> dict:
    current = get_playlist(playlist_id)
    params = {
        key: value
        for key, value in {
            "name": name,
            "description": description,
            "public": public,
            "collaborative": collaborative,
        }.items()
        if value is not None
    }
    if not params:
        raise api.SpotifyError(
            "invalid_request",
            "No playlist fields to update",
            "Specify at least one field",
        )
    if name is not None:
        params["name"] = TypeAdapter(
            Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
        ).validate_python(name)
    _options(
        current["public"] if public is None else public,
        current["collaborative"] if collaborative is None else collaborative,
    )
    data = mutation("update_playlist_details", {"playlist_id": playlist_id}, params)
    if not dry_run:
        submit_once(
            data,
            lambda: api.spotify_request(
                "PUT",
                "/playlists/" + playlist_id,
                json=params,
                required_scopes=WRITE_SCOPES,
            ),
        )
    return data


def _change_tracks(
    operation, playlist_id, track_uris, dry_run, expected_snapshot_id, position=None
):
    TypeAdapter(TrackURIs).validate_python(track_uris)
    if position is not None:
        TypeAdapter(Offset).validate_python(position)
    current = _precheck(playlist_id, expected_snapshot_id)
    if position is not None and (
        current["total"] is None or position > current["total"]
    ):
        raise api.SpotifyError(
            "invalid_position",
            "Insertion position is outside known playlist bounds",
            "Read playlist contents and select a valid position",
        )
    data = mutation(
        operation,
        {"playlist_id": playlist_id},
        {"track_uris": track_uris, "position": position},
        track_uris,
        deduplicate=operation == "remove_playlist_tracks",
    )
    data["snapshot_id"] = current["snapshot_id"]
    if dry_run:
        return data

    def before(start):
        if start:
            _precheck(playlist_id, data["snapshot_id"])

    def submit(batch, start):
        if operation == "add_playlist_tracks":
            body = {"uris": batch}
            if position is not None:
                body["position"] = position + start
            response = api.spotify_request(
                "POST",
                f"/playlists/{playlist_id}/items",
                json=body,
                required_scopes=WRITE_SCOPES,
            )
        else:
            body = {"items": [{"uri": uri} for uri in batch]}
            if data["snapshot_id"] is not None:
                body["snapshot_id"] = data["snapshot_id"]
            response = api.spotify_request(
                "DELETE",
                f"/playlists/{playlist_id}/items",
                json=body,
                required_scopes=WRITE_SCOPES,
            )
        return _snapshot(response)

    return submit_batches(data, 100, submit, before)


def add_playlist_tracks(
    playlist_id: str,
    track_uris: list[str],
    position: int | None = None,
    expected_snapshot_id: str | None = None,
    dry_run: bool = True,
) -> dict:
    return _change_tracks(
        "add_playlist_tracks",
        playlist_id,
        track_uris,
        dry_run,
        expected_snapshot_id,
        position,
    )


def remove_playlist_tracks(
    playlist_id: str,
    track_uris: list[str],
    expected_snapshot_id: str | None = None,
    dry_run: bool = True,
) -> dict:
    return _change_tracks(
        "remove_playlist_tracks", playlist_id, track_uris, dry_run, expected_snapshot_id
    )


def replace_playlist_tracks(
    playlist_id: str,
    track_uris: list[str],
    expected_snapshot_id: str | None = None,
    dry_run: bool = True,
) -> dict:
    TypeAdapter(ReplacementURIs).validate_python(track_uris)
    current = _precheck(playlist_id, expected_snapshot_id)
    data = mutation(
        "replace_playlist_tracks",
        {"playlist_id": playlist_id},
        {"track_uris": track_uris, "replaces_all": True},
        track_uris,
    )
    data["snapshot_id"] = current["snapshot_id"]
    if not dry_run:

        def submit():
            return _snapshot(
                api.spotify_request(
                    "PUT",
                    f"/playlists/{playlist_id}/items",
                    json={"uris": track_uris},
                    required_scopes=WRITE_SCOPES,
                )
            )

        data["snapshot_id"] = submit_once(data, submit).get("snapshot_id")
    return data


def reorder_playlist_tracks(
    playlist_id: str,
    range_start: int,
    insert_before: int,
    range_length: int = 1,
    expected_snapshot_id: str | None = None,
    dry_run: bool = True,
) -> dict:
    TypeAdapter(Offset).validate_python(range_start)
    TypeAdapter(Offset).validate_python(insert_before)
    TypeAdapter(Annotated[int, Field(ge=1)]).validate_python(range_length)
    current = _precheck(playlist_id, expected_snapshot_id)
    total = current["total"]
    if total is None or range_start + range_length > total or insert_before > total:
        raise api.SpotifyError(
            "invalid_position",
            "Reorder range exceeds known playlist bounds",
            "Read playlist contents and select valid positions",
        )
    body = {
        "range_start": range_start,
        "insert_before": insert_before,
        "range_length": range_length,
    }
    if current["snapshot_id"] is not None:
        body["snapshot_id"] = current["snapshot_id"]
    data = mutation("reorder_playlist_tracks", {"playlist_id": playlist_id}, body)
    data["snapshot_id"] = current["snapshot_id"]
    if not dry_run:
        data["snapshot_id"] = submit_once(
            data,
            lambda: _snapshot(
                api.spotify_request(
                    "PUT",
                    f"/playlists/{playlist_id}/items",
                    json=body,
                    required_scopes=WRITE_SCOPES,
                )
            ),
        ).get("snapshot_id")
    return data
