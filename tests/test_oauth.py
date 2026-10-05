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
