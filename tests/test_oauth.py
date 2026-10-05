from pathlib import Path

import pytest

from spotify_mcp_assistant.oauth import load_config


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
