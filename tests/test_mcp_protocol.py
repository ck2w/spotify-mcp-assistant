import asyncio
from unittest.mock import Mock

import httpx
import pytest
from fastmcp import Client

from spotify_mcp_assistant import spotify_client
from spotify_mcp_assistant.oauth import AuthorizationRequiredError
from spotify_mcp_assistant.server import mcp
from spotify_mcp_assistant.spotify_client import SpotifyError

EXPECTED_TOOLS = {
    "list_devices",
    "search_tracks",
    "get_playback_state",
    "play_track",
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
    "get_saved_tracks",
    "save_tracks",
    "remove_saved_tracks",
    "check_saved_tracks",
    "pause_playback",
    "resume_playback",
    "next_track",
    "previous_track",
    "seek_playback",
    "set_volume",
    "set_shuffle",
    "set_repeat",
    "play_playlist",
    "transfer_playback",
    "get_queue",
    "add_to_queue",
}


@pytest.mark.parametrize("device_id", ["test-mac", None])
def test_list_devices_through_mcp(monkeypatch, device_id):
    device = {
        "device_id": device_id,
        "name": "Test Mac",
        "type": "computer",
        "is_active": True,
        "is_restricted": False,
    }

    def fake_list_devices():
        return [device]

    monkeypatch.setattr(spotify_client, "list_devices", fake_list_devices)

    async def scenario():
        async with Client(mcp) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools} == EXPECTED_TOOLS

            result = await client.call_tool("list_devices", {})
            payload = result.structured_content

            assert result.is_error is False
            assert payload["ok"] is True
            assert payload["data"] == [device]
            assert payload["error"] is None

    asyncio.run(scenario())


def test_chained_default_preview_does_not_write(monkeypatch):
    track = {
        "name": "Test Song",
        "artists": ["Test Artist"],
        "track_uri": "spotify:track:" + "a" * 22,
        "url": "https://open.spotify.com/track/" + "a" * 22,
    }
    device = {
        "device_id": "test-mac",
        "name": "Test Mac",
        "type": "computer",
        "is_active": True,
        "is_restricted": False,
    }

    def fake_search(query, limit=5):
        return [track]

    def fake_devices():
        return [device]

    put = Mock(side_effect=AssertionError("Preview must not send PUT"))
    token = Mock(side_effect=AssertionError("Must not read real token"))
    monkeypatch.setattr(spotify_client, "search_tracks", fake_search)
    monkeypatch.setattr(spotify_client, "list_devices", fake_devices)
    monkeypatch.setattr(spotify_client.httpx, "put", put)
    monkeypatch.setattr(spotify_client, "get_access_token", token)

    async def scenario():
        async with Client(mcp) as client:
            search = await client.call_tool("search_tracks", {"query": "Test Song"})
            devices = await client.call_tool("list_devices", {})
            track_uri = search.structured_content["data"][0]["track_uri"]
            device_id = devices.structured_content["data"][0]["device_id"]

            result = await client.call_tool(
                "play_track",
                {"track_uri": track_uri, "device_id": device_id},
            )
            payload = result.structured_content
            assert payload["ok"] is True
            assert payload["data"]["status"] == "preview"
            assert payload["data"]["track_uri"] == track_uri
            assert payload["data"]["device_id"] == device_id

    asyncio.run(scenario())
    put.assert_not_called()
    token.assert_not_called()


@pytest.mark.parametrize("limit", [0, 11])
def test_invalid_limit_is_rejected(monkeypatch, limit):
    search = Mock(side_effect=AssertionError("Must reject before API call"))
    monkeypatch.setattr(spotify_client, "search_tracks", search)

    async def scenario():
        async with Client(mcp) as client:
            result = await client.call_tool(
                "search_tracks",
                {"query": "Yellow", "limit": limit},
                raise_on_error=False,
            )
            assert result.is_error is True

    asyncio.run(scenario())
    search.assert_not_called()


def test_rate_limit_returns_structured_error(monkeypatch):
    failure = SpotifyError(
        "rate_limited",
        "Too many requests",
        "Wait before retrying",
        retryable=True,
        retry_after_seconds=30,
    )
    search = Mock(side_effect=failure)
    monkeypatch.setattr(spotify_client, "search_tracks", search)

    async def scenario():
        async with Client(mcp) as client:
            result = await client.call_tool("search_tracks", {"query": "Yellow"})
            payload = result.structured_content
            assert result.is_error is False
            assert payload["ok"] is False
            assert payload["data"] is None
            assert payload["error"]["code"] == "rate_limited"
            assert payload["error"]["retryable"] is True
            assert payload["error"]["retry_after_seconds"] == 30
            assert payload["error"]["next_action"] == "Wait before retrying"

    asyncio.run(scenario())
    search.assert_called_once()


def test_empty_playback_through_mcp(monkeypatch):
    monkeypatch.setattr(
        spotify_client, "get_access_token", Mock(return_value="fake-token")
    )
    monkeypatch.setattr(
        spotify_client.httpx,
        "get",
        Mock(return_value=httpx.Response(204)),
    )

    async def scenario():
        async with Client(mcp) as client:
            result = await client.call_tool("get_playback_state", {})
            payload = result.structured_content
            assert payload["ok"] is True
            assert payload["data"] == {
                "has_playback": False,
                "is_playing": False,
                "progress_ms": None,
                "track": None,
                "device": None,
                "shuffle_state": None,
                "repeat_state": None,
                "context_uri": None,
            }

    asyncio.run(scenario())


def test_authorization_required_through_mcp(monkeypatch):
    token = Mock(side_effect=AuthorizationRequiredError("Test failure"))
    get = Mock(side_effect=AssertionError("Must not contact Spotify"))
    monkeypatch.setattr(spotify_client, "get_access_token", token)
    monkeypatch.setattr(spotify_client.httpx, "get", get)

    async def scenario():
        async with Client(mcp) as client:
            result = await client.call_tool("list_devices", {})
            payload = result.structured_content
            assert payload["ok"] is False
            assert payload["error"]["code"] == "auth_required"
            assert "spotify-mcp-auth" in payload["error"]["next_action"]
            assert payload["error"]["retryable"] is False

    asyncio.run(scenario())
    get.assert_not_called()


def test_server_factories_and_execution_schemas():
    from spotify_mcp_assistant.server import create_server

    direct = {
        "pause_playback",
        "resume_playback",
        "next_track",
        "previous_track",
        "seek_playback",
        "set_volume",
        "set_shuffle",
        "set_repeat",
    }

    async def scenario():
        for server in (create_server(), create_server()):
            async with Client(server) as client:
                tools = await client.list_tools()
                assert len(tools) == len({tool.name for tool in tools}) == 32
                assert {tool.name for tool in tools} == EXPECTED_TOOLS
                for tool in tools:
                    properties = tool.input_schema.get("properties", {})
                    if tool.name in direct:
                        assert "dry_run" not in properties
                    elif tool.annotations.read_only_hint is False:
                        assert properties["dry_run"]["default"] is True
                queue = next(tool for tool in tools if tool.name == "get_queue")
                assert queue.input_schema.get("properties", {}) == {}

    asyncio.run(scenario())


def test_mcp_batch_error_preserves_partial_data(fake_http, fake_uris):
    fake_http.enqueue_playlist_precheck(total=0)
    fake_http.enqueue(httpx.Response(201, json={"snapshot_id": "first"}))
    fake_http.enqueue_playlist_precheck(total=100, snapshot="first")
    fake_http.enqueue(httpx.ReadTimeout("fake"))

    async def scenario():
        async with Client(mcp) as client:
            response = await client.call_tool(
                "add_playlist_tracks",
                {
                    "playlist_id": "p" * 22,
                    "track_uris": fake_uris(201),
                    "dry_run": False,
                },
            )
            payload = response.structured_content
            assert not response.is_error
            assert payload["ok"] is False
            assert payload["data"]["submitted_ranges"] == [[0, 100]]
            assert payload["data"]["unknown_range"] == [100, 200]
            assert payload["error"]["code"] == "write_result_unknown"

    asyncio.run(scenario())
