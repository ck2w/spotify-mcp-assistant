import httpx
import pytest

from spotify_mcp_assistant import spotify_client as api


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
@pytest.mark.parametrize("failure", [httpx.ReadTimeout("fake"), httpx.Response(500)])
def test_write_failure_is_unknown_without_replay(fake_http, method, failure):
    fake_http.enqueue(failure)
    with pytest.raises(api.SpotifyError) as caught:
        api.spotify_request(method, "/me/playlists", json={"name": "Test"})
    assert caught.value.error["code"] == "write_result_unknown"
    assert len(fake_http.calls) == 1
    assert fake_http.calls[0]["timeout"] == 15


@pytest.mark.parametrize("status,code", [(401, "auth_required"), (429, "rate_limited")])
def test_write_rejection_is_not_retried(fake_http, status, code):
    fake_http.enqueue(httpx.Response(status, headers={"Retry-After": "30"}))
    with pytest.raises(api.SpotifyError) as caught:
        api.spotify_request("PUT", "/me/player/pause")
    assert caught.value.error["code"] == code
    assert len(fake_http.calls) == 1


def test_get_refreshes_once(fake_http):
    fake_http.enqueue(httpx.Response(401))
    fake_http.enqueue(httpx.Response(200, json={}))
    assert api.spotify_request("GET", "/me/player").status_code == 200
    assert len(fake_http.calls) == 2


def test_second_get_401_stops(fake_http):
    fake_http.enqueue(httpx.Response(401))
    fake_http.enqueue(httpx.Response(401))
    with pytest.raises(api.SpotifyError):
        api.spotify_request("GET", "/me/player")
    assert len(fake_http.calls) == 2


def test_empty_write_response(fake_http):
    fake_http.enqueue(httpx.Response(204))
    assert api.spotify_request("PUT", "/me/player/pause").status_code == 204


def test_non_numeric_retry_after(fake_http):
    fake_http.enqueue(httpx.Response(429, headers={"Retry-After": "later"}))
    with pytest.raises(api.SpotifyError) as caught:
        api.spotify_request("GET", "/me/player")
    assert "retry_after_seconds" not in caught.value.error


def test_token_failure_is_not_unknown(fake_http, monkeypatch):
    def fail(**kw):
        raise httpx.ReadTimeout("refresh failed")

    monkeypatch.setattr(api, "get_access_token", fail)
    with pytest.raises(api.SpotifyError) as caught:
        api.spotify_request("POST", "/me/playlists")
    assert caught.value.error["code"] == "network_error"
    assert fake_http.calls == []


def test_missing_scope_prevents_request(fake_http, monkeypatch):
    from spotify_mcp_assistant import oauth

    def fail(**kw):
        raise oauth.InsufficientScopeError(("user-library-modify",))

    monkeypatch.setattr(api, "get_access_token", fail)
    with pytest.raises(api.SpotifyError) as caught:
        api.spotify_request(
            "PUT", "/me/library", required_scopes=("user-library-modify",)
        )
    assert caught.value.error["code"] == "insufficient_scope"
    assert "user-library-modify" in caught.value.error["message"]
    assert fake_http.calls == []


def test_corrupt_cache_is_sanitized(fake_http, monkeypatch):
    def fail(**kw):
        raise ValueError("secret-test-value")

    monkeypatch.setattr(api, "get_access_token", fail)
    with pytest.raises(api.SpotifyError) as caught:
        api.spotify_request("PUT", "/me/library")
    assert caught.value.error["code"] == "oauth_config_error"
    assert "secret-test-value" not in str(caught.value.error)
    assert fake_http.calls == []


def test_lock_timeout_maps_to_retryable_auth_busy(monkeypatch):
    import pytest

    from spotify_mcp_assistant import spotify_client
    from spotify_mcp_assistant.setup_types import LockTimeoutError

    monkeypatch.setattr(
        spotify_client,
        "get_access_token",
        lambda **k: (_ for _ in ()).throw(LockTimeoutError()),
    )
    with pytest.raises(spotify_client.SpotifyError) as failure:
        spotify_client.spotify_request("PUT", "/me/player/pause")
    assert failure.value.error["code"] == "auth_busy"
    assert failure.value.error["retryable"] is True
