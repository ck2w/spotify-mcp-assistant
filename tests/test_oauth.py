from pathlib import Path

import pytest

from spotify_mcp_assistant.oauth import load_config


def test_save_token_permissions(tmp_path):
    from spotify_mcp_assistant.oauth import save_token

    path = tmp_path / "token"
    path.write_text("old")
    path.chmod(0o644)
    save_token({"access_token": "fake"}, path)
    assert path.stat().st_mode & 0o777 == 0o600


def test_main_failed_authorization_preserves_cache(tmp_path, monkeypatch):
    from spotify_mcp_assistant import oauth

    monkeypatch.setenv("SPOTIFY_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(oauth, "load_config", lambda _: {})
    monkeypatch.setattr(oauth, "authorize", lambda _: (_ for _ in ()).throw(ValueError("denied")), raising=False)
    token = tmp_path / ".spotify_token.json"
    token.write_text('{"access_token":"keep"}')
    with pytest.raises(ValueError, match="denied"):
        oauth.main()
    assert token.read_text() == '{"access_token":"keep"}'


def test_refresh_token_returns_copy_with_preserved_metadata(monkeypatch):
    import httpx
    from spotify_mcp_assistant import oauth

    old = {"refresh_token": "old-refresh", "scope": "user-library-read"}
    monkeypatch.setattr(oauth.httpx, "post", lambda *a, **k: httpx.Response(200, json={"access_token": "new", "expires_in": 3600}, request=httpx.Request("POST", "https://example.test")))
    new = oauth.refresh_token({"SPOTIFY_CLIENT_ID": "fake", "SPOTIFY_CLIENT_SECRET": "fake"}, old)
    assert new["refresh_token"] == "old-refresh"
    assert new["scope"] == "user-library-read"
    assert new["access_token"] == "new"
    assert "access_token" not in old


def refresh_worker(directory, starting, release, results, count):
    import os
    import httpx
    from spotify_mcp_assistant import oauth

    os.environ["SPOTIFY_CONFIG_DIR"] = directory
    oauth.load_config = lambda _: {"SPOTIFY_CLIENT_ID": "fake", "SPOTIFY_CLIENT_SECRET": "fake"}

    def post(*args, **kwargs):
        with count.get_lock():
            count.value += 1
        assert release.wait(5)
        return httpx.Response(200, json={"access_token": "new", "expires_in": 3600}, request=httpx.Request("POST", "https://example.test"))

    oauth.httpx.post = post
    starting.wait()
    results.put(oauth.get_access_token())


def test_concurrent_refresh_rechecks_cache(tmp_path):
    import json
    import multiprocessing
    import time

    (tmp_path / ".spotify_token.json").write_text(json.dumps({"access_token": "old", "refresh_token": "old-refresh", "expires_at": 0}))
    ctx = multiprocessing.get_context("spawn")
    start, release, results, count = ctx.Barrier(3), ctx.Event(), ctx.Queue(), ctx.Value("i", 0)
    workers = [ctx.Process(target=refresh_worker, args=(str(tmp_path), start, release, results, count)) for _ in range(2)]
    for worker in workers:
        worker.start()
    start.wait(timeout=5)
    deadline = time.monotonic() + 5
    while count.value == 0 and time.monotonic() < deadline:
        time.sleep(0.01)
    release.set()
    try:
        assert results.get(timeout=5) == "new"
        assert results.get(timeout=5) == "new"
    finally:
        for worker in workers:
            worker.join(5)
            if worker.is_alive():
                worker.terminate()
                worker.join()
    assert count.value == 1


def test_missing_config_reports_variable_names(tmp_path, monkeypatch):
    names = [
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_REDIRECT_URI",
    ]

    for name in names:
        monkeypatch.delenv(name, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        load_config(env_file)

    for name in names:
        assert name in str(error.value)


def test_config_directory_resolution(tmp_path, monkeypatch):
    from spotify_mcp_assistant.oauth import get_config_dir

    monkeypatch.delenv("SPOTIFY_CONFIG_DIR", raising=False)
    assert get_config_dir() == Path.home() / ".config" / "spotify-mcp-assistant"
    chosen = tmp_path / "private-config"
    monkeypatch.setenv("SPOTIFY_CONFIG_DIR", str(chosen))
    monkeypatch.chdir(tmp_path)
    assert get_config_dir() == chosen
    monkeypatch.setenv("SPOTIFY_CONFIG_DIR", "~/spotify-mcp-test")
    assert get_config_dir() == Path.home() / "spotify-mcp-test"
    for invalid in ("relative-config", ""):
        monkeypatch.setenv("SPOTIFY_CONFIG_DIR", invalid)
        with pytest.raises(ValueError, match="SPOTIFY_CONFIG_DIR"):
            get_config_dir()


def test_authorization_requests_management_scopes():
    from urllib.parse import parse_qs, urlsplit

    from spotify_mcp_assistant import oauth

    url, state = oauth.build_authorization_url(
        {
            "SPOTIFY_CLIENT_ID": "fake",
            "SPOTIFY_REDIRECT_URI": "http://127.0.0.1:8888/callback",
        }
    )
    assert set(parse_qs(urlsplit(url).query)["scope"][0].split()) == {
        "user-read-playback-state",
        "user-read-currently-playing",
        "user-modify-playback-state",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-private",
        "playlist-modify-public",
        "user-library-read",
        "user-library-modify",
    }
    assert state


@pytest.mark.parametrize("scope", [None, "user-library-read"])
def test_cached_scope_compatibility(tmp_path, monkeypatch, scope):
    import json
    import time

    from spotify_mcp_assistant import oauth

    monkeypatch.setenv("SPOTIFY_CONFIG_DIR", str(tmp_path))
    token = {"access_token": "fake", "expires_at": time.time() + 3600}
    if scope is not None:
        token["scope"] = scope
    (tmp_path / ".spotify_token.json").write_text(json.dumps(token))
    assert oauth.get_access_token(required_scopes=("user-library-read",)) == "fake"
    if scope is not None:
        with pytest.raises(oauth.InsufficientScopeError):
            oauth.get_access_token(required_scopes=("user-library-modify",))


@pytest.mark.parametrize("scope", [None, "user-read-playback-state"])
def test_refresh_without_scope_preserves_knowledge(tmp_path, monkeypatch, scope):
    import json
    import time

    import httpx

    from spotify_mcp_assistant import oauth

    monkeypatch.setenv("SPOTIFY_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr(
        oauth,
        "load_config",
        lambda _: {"SPOTIFY_CLIENT_ID": "fake", "SPOTIFY_CLIENT_SECRET": "fake"},
    )
    token = {
        "access_token": "old",
        "refresh_token": "fake-refresh",
        "expires_at": time.time() - 1,
    }
    if scope is not None:
        token["scope"] = scope
    cache = tmp_path / ".spotify_token.json"
    cache.write_text(json.dumps(token))
    response = httpx.Response(
        200,
        json={"access_token": "new", "expires_in": 3600},
        request=httpx.Request("POST", "https://accounts.spotify.com/api/token"),
    )
    monkeypatch.setattr(oauth.httpx, "post", lambda *a, **kw: response)
    assert oauth.get_access_token() == "new"
    refreshed = json.loads(cache.read_text())
    assert refreshed.get("scope") == scope
    assert refreshed["refresh_token"] == "fake-refresh"
