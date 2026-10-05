from collections import deque
from urllib.parse import urlsplit

import httpx
import pytest


class FakeHTTP:
    def __init__(self):
        self.responses = deque()
        self.calls = []

    def enqueue(self, response):
        self.responses.append(response)

    def enqueue_devices(self, devices):
        self.enqueue(httpx.Response(200, json={"devices": devices}))

    def enqueue_playlist_precheck(self, total=0, snapshot="before", **fields):
        self.enqueue(
            httpx.Response(
                200,
                json={
                    "id": "p" * 22,
                    "uri": "spotify:playlist:" + "p" * 22,
                    "name": "Test",
                    "external_urls": {
                        "spotify": "https://open.spotify.com/playlist/" + "p" * 22
                    },
                    "owner": {"id": "fake-user"},
                    "public": False,
                    "collaborative": False,
                    "snapshot_id": snapshot,
                    "items": {"total": total},
                    **fields,
                },
            )
        )

    def enqueue_playlist_items(self, items, offset=0, next=None):
        self.enqueue(
            httpx.Response(
                200,
                json={
                    "items": [
                        {"item": item, "added_at": None, "is_local": False}
                        for item in items
                    ],
                    "offset": offset,
                    "total": len(items),
                    "next": next,
                },
            )
        )

    @property
    def write_calls(self):
        return [call for call in self.calls if call["method"] != "GET"]

    @property
    def write_count(self):
        return len(self.write_calls)

    def request(self, method, url, **kwargs):
        self.calls.append(
            {"method": method, "path": urlsplit(url).path.removeprefix("/v1"), **kwargs}
        )
        assert self.responses, f"Unexpected {method} {url}"
        response = self.responses.popleft()
        if isinstance(response, Exception):
            raise response
        response.request = httpx.Request(method, url)
        return response


@pytest.fixture
def fake_http(monkeypatch):
    from spotify_mcp_assistant import spotify_client

    fake = FakeHTTP()
    for method in ("get", "post", "put", "delete"):
        monkeypatch.setattr(
            httpx,
            method,
            lambda url, _method=method, **kw: fake.request(_method.upper(), url, **kw),
        )
    monkeypatch.setattr(spotify_client, "get_access_token", lambda **kw: "fake-token")
    return fake


@pytest.fixture
def fake_device():
    return {
        "id": "test-mac",
        "name": "Test Mac",
        "type": "computer",
        "is_active": True,
        "is_restricted": False,
    }


@pytest.fixture
def fake_track():
    return {
        "type": "track",
        "name": "Test Song",
        "artists": [{"name": "Test Artist"}],
        "uri": "spotify:track:" + "a" * 22,
        "external_urls": {"spotify": "https://open.spotify.com/track/" + "a" * 22},
    }


@pytest.fixture
def fake_uris():
    return lambda n: ["spotify:track:" + str(i).zfill(22) for i in range(n)]
