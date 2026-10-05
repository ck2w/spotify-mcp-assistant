import httpx
import pytest


@pytest.mark.parametrize(
    "name,method", [("save_tracks", "PUT"), ("remove_saved_tracks", "DELETE")]
)
def test_library_chunks_uris_query_and_deduplicates(fake_http, fake_uris, name, method):
    from spotify_mcp_assistant import library

    fake_http.enqueue(httpx.Response(200))
    fake_http.enqueue(httpx.Response(200))
    uris = fake_uris(41) + fake_uris(1)
    result = getattr(library, name)(uris, dry_run=False)
    assert result["submitted_count"] == 41
    assert result["input_indices"][0] == [0, 41]
    assert [call["method"] for call in fake_http.calls] == [method, method]
    assert fake_http.calls[0]["params"] == {"uris": ",".join(uris[:40])}
    assert fake_http.calls[1]["params"] == {"uris": uris[40]}


@pytest.mark.parametrize(
    "name,arg",
    [
        ("save_tracks", ["spotify:track:" + "a" * 22]),
        ("remove_saved_tracks", ["spotify:track:" + "a" * 22]),
        ("save_playlist", "spotify:playlist:" + "p" * 22),
        ("unsave_playlist", "spotify:playlist:" + "p" * 22),
    ],
)
def test_library_default_preview(fake_http, name, arg):
    from spotify_mcp_assistant import library

    assert getattr(library, name)(arg)["status"] == "preview"
    assert fake_http.calls == []


def test_check_failure_keeps_known_results(fake_http, fake_uris):
    from spotify_mcp_assistant import library, spotify_client

    fake_http.enqueue(httpx.Response(200, json=[True] * 40))
    fake_http.enqueue(httpx.Response(429))
    with pytest.raises(spotify_client.SpotifyError) as caught:
        library.check_saved_tracks(fake_uris(41))
    assert len(caught.value.data["items"]) == 40
    assert caught.value.data["unqueried_uris"] == fake_uris(41)[40:]


def test_check_keeps_duplicate_input_order(fake_http):
    from spotify_mcp_assistant import library

    a, b = "spotify:track:" + "a" * 22, "spotify:track:" + "b" * 22
    fake_http.enqueue(httpx.Response(200, json=[True, False, True]))
    assert library.check_saved_tracks([a, b, a])["items"] == [
        {"track_uri": a, "saved": True},
        {"track_uri": b, "saved": False},
        {"track_uri": a, "saved": True},
    ]


def test_check_malformed_response_does_not_truncate(fake_http):
    from spotify_mcp_assistant import library, spotify_client

    fake_http.enqueue(httpx.Response(200, json=[]))
    with pytest.raises(spotify_client.SpotifyError) as caught:
        library.check_saved_tracks(["spotify:track:" + "a" * 22])
    assert caught.value.error["code"] == "spotify_response_error"
    assert caught.value.data["items"] == []


@pytest.mark.parametrize("count", [0, 501])
def test_library_rejects_out_of_bounds(fake_http, fake_uris, count):
    from pydantic import ValidationError

    from spotify_mcp_assistant import library

    with pytest.raises(ValidationError):
        library.save_tracks(fake_uris(count))
    assert fake_http.calls == []


def test_saved_tracks_page(fake_http, fake_track):
    from spotify_mcp_assistant import library

    fake_http.enqueue(
        httpx.Response(
            200,
            json={
                "items": [{"track": fake_track, "added_at": "2026-01-01T00:00:00Z"}],
                "total": 1,
                "next": None,
            },
        )
    )
    data = library.get_saved_tracks()
    assert data["items"][0]["track"]["name"] == "Test Song"
    assert data["next_offset"] is None
    assert fake_http.calls[0]["path"] == "/me/tracks"


def test_unsave_playlist_uses_library(fake_http):
    from spotify_mcp_assistant import library

    fake_http.enqueue(httpx.Response(200))
    library.unsave_playlist("spotify:playlist:" + "p" * 22, dry_run=False)
    assert fake_http.calls[0]["path"] == "/me/library"
    assert fake_http.calls[0]["method"] == "DELETE"
