import asyncio

import httpx
import pytest
from fastmcp import Client


def test_page_preserves_non_track_positions(fake_http, fake_track):
    from spotify_mcp_assistant import playlists

    fake_http.enqueue_playlist_items([None, {"type": "episode"}, fake_track])
    result = playlists.get_playlist_tracks("p" * 22)
    assert [entry["position"] for entry in result["items"]] == [0, 1, 2]
    assert result["items"][0]["track"] is None
    assert result["items"][1]["item_type"] == "episode"
    assert result["items"][2]["track"]["name"] == "Test Song"
    assert result["next_offset"] is None


@pytest.mark.parametrize("field", ["track", "item"])
def test_playlist_content_field_variants(fake_http, fake_track, field):
    from spotify_mcp_assistant import playlists

    fake_http.enqueue(
        httpx.Response(
            200,
            json={
                "items": [{field: fake_track}],
                "next": "https://api.spotify.com/v1/playlists/x/items?offset=21&limit=20",
                "total": 30,
            },
        )
    )
    result = playlists.get_playlist_tracks("p" * 22, offset=20)
    assert result["items"][0]["position"] == 20
    assert result["next_offset"] == 21


def test_missing_content_is_not_empty_playlist(fake_http):
    from spotify_mcp_assistant import playlists

    fake_http.enqueue_playlist_precheck()
    assert playlists.get_playlist("p" * 22)["contents_accessible"] is True
    fake_http.enqueue(
        httpx.Response(
            200,
            json={
                "id": "p" * 22,
                "name": "Other",
                "uri": "spotify:playlist:" + "p" * 22,
            },
        )
    )
    assert playlists.get_playlist("p" * 22)["contents_accessible"] is False


@pytest.mark.parametrize("args", [{"limit": 0}, {"limit": 51}, {"offset": -1}])
def test_playlist_page_schema_rejects_bad_bounds(args):
    from spotify_mcp_assistant.server import mcp

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool(
                "list_playlists", args, raise_on_error=False
            )
            assert result.is_error

    asyncio.run(run())


@pytest.mark.parametrize(
    "name,args",
    [
        ("create_playlist", {"name": "Test"}),
        ("update_playlist_details", {"playlist_id": "p" * 22, "description": ""}),
        (
            "add_playlist_tracks",
            {"playlist_id": "p" * 22, "track_uris": ["spotify:track:" + "a" * 22]},
        ),
        (
            "remove_playlist_tracks",
            {"playlist_id": "p" * 22, "track_uris": ["spotify:track:" + "a" * 22]},
        ),
        ("replace_playlist_tracks", {"playlist_id": "p" * 22, "track_uris": []}),
        (
            "reorder_playlist_tracks",
            {"playlist_id": "p" * 22, "range_start": 0, "insert_before": 2},
        ),
    ],
)
def test_playlist_mutations_preview_by_default(fake_http, name, args):
    from spotify_mcp_assistant import playlists

    if name != "create_playlist":
        fake_http.enqueue_playlist_precheck(total=3)
    result = getattr(playlists, name)(**args)
    assert result["status"] == "preview"
    assert result["submitted_count"] == 0
    assert fake_http.write_count == 0


def test_create_is_private_and_returns_real_id(fake_http):
    from spotify_mcp_assistant import playlists

    fake_http.enqueue(
        httpx.Response(
            201,
            json={
                "id": "q" * 22,
                "uri": "spotify:playlist:" + "q" * 22,
                "external_urls": {
                    "spotify": "https://open.spotify.com/playlist/" + "q" * 22
                },
            },
        )
    )
    data = playlists.create_playlist("Test", dry_run=False)
    assert data["playlist_id"] == "q" * 22
    assert fake_http.write_calls[0]["path"] == "/me/playlists"
    assert fake_http.write_calls[0]["json"]["public"] is False


@pytest.mark.parametrize(
    "failure,status",
    [(httpx.ReadTimeout("fake"), "unknown"), (httpx.Response(429), "partial")],
)
def test_add_second_batch_failure_keeps_progress(fake_http, fake_uris, failure, status):
    from spotify_mcp_assistant import playlists, spotify_client

    fake_http.enqueue_playlist_precheck(total=0)
    fake_http.enqueue(httpx.Response(201, json={"snapshot_id": "first"}))
    fake_http.enqueue_playlist_precheck(total=100, snapshot="first")
    fake_http.enqueue(failure)
    with pytest.raises(spotify_client.SpotifyError) as caught:
        playlists.add_playlist_tracks("p" * 22, fake_uris(201), dry_run=False)
    data = caught.value.data
    assert data["status"] == status
    assert data["submitted_ranges"] == [[0, 100]]
    assert data["unknown_range" if status == "unknown" else "failed_range"] == [
        100,
        200,
    ]
    assert data["not_attempted_ranges"] == [[200, 201]]
    assert fake_http.write_count == 2


def test_add_batches_keep_insert_position_and_duplicates(fake_http, fake_uris):
    from spotify_mcp_assistant import playlists

    fake_http.enqueue_playlist_precheck(total=10)
    fake_http.enqueue(httpx.Response(201, json={"snapshot_id": "first"}))
    fake_http.enqueue_playlist_precheck(total=110, snapshot="first")
    fake_http.enqueue(httpx.Response(201, json={"snapshot_id": "second"}))
    uris = fake_uris(100) + [fake_uris(1)[0]]
    result = playlists.add_playlist_tracks("p" * 22, uris, position=3, dry_run=False)
    assert [call["json"]["position"] for call in fake_http.write_calls] == [3, 103]
    assert result["submitted_count"] == 101
    assert result["normalized_uris"] == uris


def test_snapshot_conflict_does_not_write(fake_http):
    from spotify_mcp_assistant import playlists, spotify_client

    fake_http.enqueue_playlist_precheck(snapshot="new")
    with pytest.raises(spotify_client.SpotifyError) as caught:
        playlists.replace_playlist_tracks(
            "p" * 22, [], expected_snapshot_id="old", dry_run=False
        )
    assert caught.value.error["code"] == "conflict"
    assert fake_http.write_count == 0


def test_collaborative_update_checks_current_public(fake_http):
    from spotify_mcp_assistant import playlists, spotify_client

    fake_http.enqueue_playlist_precheck(public=True)
    with pytest.raises(spotify_client.SpotifyError):
        playlists.update_playlist_details("p" * 22, collaborative=True, dry_run=False)
    assert fake_http.write_count == 0


def test_replace_clear_and_maximum(fake_http, fake_uris):
    from pydantic import ValidationError

    from spotify_mcp_assistant import playlists

    with pytest.raises(ValidationError):
        playlists.replace_playlist_tracks("p" * 22, fake_uris(101))
    fake_http.enqueue_playlist_precheck(total=3)
    fake_http.enqueue(httpx.Response(200, json={"snapshot_id": "empty"}))
    playlists.replace_playlist_tracks("p" * 22, [], dry_run=False)
    assert fake_http.write_calls[0]["json"] == {"uris": []}


def test_remove_normalizes_duplicate_indices(fake_http):
    from spotify_mcp_assistant import playlists

    uri = "spotify:track:" + "a" * 22
    fake_http.enqueue_playlist_precheck(total=3)
    fake_http.enqueue(httpx.Response(200, json={"snapshot_id": "removed"}))
    data = playlists.remove_playlist_tracks("p" * 22, [uri, uri], dry_run=False)
    assert data["input_indices"] == [[0, 1]]
    assert data["submitted_count"] == 1
    assert fake_http.write_calls[0]["json"]["items"] == [{"uri": uri}]


def test_reorder_counts_all_item_types(fake_http):
    from spotify_mcp_assistant import playlists

    fake_http.enqueue_playlist_precheck(total=3)
    fake_http.enqueue(httpx.Response(200, json={"snapshot_id": "moved"}))
    playlists.reorder_playlist_tracks(
        "p" * 22, range_start=2, insert_before=0, dry_run=False
    )
    assert fake_http.write_calls[0]["json"]["range_start"] == 2
