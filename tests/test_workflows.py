"""MCP workflow contract simulations; these do not test LLM confirmation behavior."""

import asyncio

import httpx
from fastmcp import Client

from spotify_mcp_assistant.server import create_server


def test_create_add_read_workflow(fake_http, fake_track):
    fake_http.enqueue(httpx.Response(200, json={"tracks": {"items": [fake_track]}}))
    fake_http.enqueue(
        httpx.Response(
            201, json={"id": "p" * 22, "uri": "spotify:playlist:" + "p" * 22}
        )
    )
    fake_http.enqueue_playlist_precheck(total=0)
    fake_http.enqueue_playlist_precheck(total=0)
    fake_http.enqueue(httpx.Response(201, json={"snapshot_id": "new"}))
    fake_http.enqueue_playlist_items([fake_track])

    async def scenario():
        async with Client(create_server()) as client:

            async def call(name, args):
                payload = (await client.call_tool(name, args)).structured_content
                assert payload["ok"] is True
                return payload["data"]

            tracks = await call("search_tracks", {"query": "Test Song"})
            preview = await call("create_playlist", {"name": "Test"})
            assert preview["status"] == "preview" and preview["playlist_id"] is None
            created = await call("create_playlist", {"name": "Test", "dry_run": False})
            target = created["playlist_id"]
            args = {"playlist_id": target, "track_uris": [tracks[0]["track_uri"]]}
            preview = await call("add_playlist_tracks", args)
            args.update(dry_run=False, expected_snapshot_id=preview["snapshot_id"])
            await call("add_playlist_tracks", args)
            page = await call("get_playlist_tracks", {"playlist_id": target})
            assert page["items"][0]["track"]["track_uri"] == tracks[0]["track_uri"]
            assert page["has_more"] is False

    asyncio.run(scenario())
    assert fake_http.write_count == 2


def test_playlist_play_verify_pause_queue_workflow(fake_http, fake_device, fake_track):
    fake_http.enqueue_devices([fake_device])
    fake_http.enqueue_devices([fake_device])
    fake_http.enqueue(httpx.Response(204))
    fake_http.enqueue(
        httpx.Response(
            200,
            json={
                "is_playing": True,
                "item": fake_track,
                "device": fake_device,
                "context": {"uri": "spotify:playlist:" + "p" * 22},
            },
        )
    )
    fake_http.enqueue_devices([fake_device])
    fake_http.enqueue(httpx.Response(204))
    fake_http.enqueue_devices([fake_device])
    fake_http.enqueue_devices([fake_device])
    fake_http.enqueue(httpx.Response(204))
    fake_http.enqueue(
        httpx.Response(
            200, json={"currently_playing": fake_track, "queue": [fake_track]}
        )
    )

    async def scenario():
        async with Client(create_server()) as client:

            async def call(name, args):
                payload = (await client.call_tool(name, args)).structured_content
                assert payload["ok"] is True
                return payload["data"]

            args = {
                "playlist_uri": "spotify:playlist:" + "p" * 22,
                "device_id": "test-mac",
            }
            assert (await call("play_playlist", args))["status"] == "preview"
            await call("play_playlist", {**args, "dry_run": False})
            state = await call("get_playback_state", {})
            assert (
                state["context_uri"] == args["playlist_uri"]
                and state["device"]["device_id"] == "test-mac"
                and state["is_playing"]
            )
            await call("pause_playback", {"device_id": "test-mac"})
            queue_args = {"track_uri": fake_track["uri"], "device_id": "test-mac"}
            await call("add_to_queue", queue_args)
            await call("add_to_queue", {**queue_args, "dry_run": False})
            assert (await call("get_queue", {}))["queue"][0]["track"][
                "track_uri"
            ] == fake_track["uri"]

    asyncio.run(scenario())


def test_save_check_remove_workflow(fake_http):
    for response in [
        httpx.Response(200, json=[False]),
        httpx.Response(200),
        httpx.Response(200, json=[True]),
        httpx.Response(200),
        httpx.Response(200, json=[False]),
    ]:
        fake_http.enqueue(response)

    async def scenario():
        async with Client(create_server()) as client:
            args = {"track_uris": ["spotify:track:" + "a" * 22]}

            async def call(name, args):
                payload = (await client.call_tool(name, args)).structured_content
                assert payload["ok"]
                return payload["data"]

            assert (await call("check_saved_tracks", args))["items"][0][
                "saved"
            ] is False
            for name, want in [("save_tracks", True), ("remove_saved_tracks", False)]:
                assert (await call(name, args))["status"] == "preview"
                await call(name, {**args, "dry_run": False})
                assert (await call("check_saved_tracks", args))["items"][0][
                    "saved"
                ] is want

    asyncio.run(scenario())
