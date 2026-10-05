import json
from pathlib import Path

import pytest


@pytest.fixture
def launch(tmp_path):
    from spotify_mcp_assistant.setup_types import LaunchSpec
    return LaunchSpec("/persistent/bin/spotify-mcp-assistant", (), tmp_path / "private", "0.3.0")


@pytest.mark.parametrize("client,relative", [("claude-desktop", "Library/Application Support/Claude/claude_desktop_config.json"), ("claude-code", ".claude.json"), ("codex", ".codex/config.toml"), ("cursor", ".cursor/mcp.json")])
def test_client_paths(client, relative, tmp_path):
    from spotify_mcp_assistant.client_config import client_path
    assert client_path(client, tmp_path, None) == tmp_path / relative


@pytest.mark.parametrize("value", ["", "relative", "/not-existing-spotify-setup-dir"])
def test_invalid_codex_home(value, tmp_path):
    from spotify_mcp_assistant.client_config import client_path
    from spotify_mcp_assistant.setup_types import SetupError
    with pytest.raises(SetupError):
        client_path("codex", tmp_path, value)


def test_custom_codex_home(tmp_path):
    from spotify_mcp_assistant.client_config import client_path
    assert client_path("codex", Path("/other"), str(tmp_path)) == tmp_path / "config.toml"


@pytest.mark.parametrize("client", ["claude-desktop", "claude-code", "cursor"])
def test_json_preserves_other_servers_and_policy(client, launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    old = {"theme": "keep", "mcpServers": {"other": {"command": "keep"}, "spotify": {"command": "/old/spotify-mcp-assistant", "env": {"OTHER": "keep"}, "disabled": True, "autoApprove": []}}}
    result = merge_client_config(client, json.dumps(old), launch)
    data = json.loads(result.text)
    assert data["theme"] == "keep"
    assert data["mcpServers"]["other"] == {"command": "keep"}
    spotify = data["mcpServers"]["spotify"]
    assert spotify["disabled"] is True
    assert spotify["autoApprove"] == []
    assert spotify["env"]["OTHER"] == "keep"
    assert spotify["env"]["SPOTIFY_CONFIG_DIR"] == str(launch.config_dir)
    assert spotify["command"] == "/persistent/bin/spotify-mcp-assistant"
    assert not merge_client_config(client, result.text, launch).changed


def test_codex_preserves_comments_and_policy(launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    old = '# comment\nmodel = "keep"\n[mcp_servers.spotify]\nenabled = false\ncommand = "/old/spotify-mcp-assistant"\n'
    result = merge_client_config("codex", old, launch)
    assert '# comment' in result.text
    assert 'enabled = false' in result.text
    assert 'model = "keep"' in result.text
    assert not merge_client_config("codex", result.text, launch).changed


@pytest.mark.parametrize("client,text", [("cursor", '[]'), ("cursor", '{"mcpServers": []}'), ("cursor", '{"a":1,"a":2}'), ("cursor", '// comment\n{}'), ("cursor", '{"mcpServers":{"spotify":{"env":[]}}}'), ("codex", '[mcp_servers]\nspotify = 1'), ("codex", '[a]\n[a]')])
def test_invalid_structure_rejected(client, text, launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    from spotify_mcp_assistant.setup_types import SetupError
    with pytest.raises(SetupError):
        merge_client_config(client, text, launch)


def test_remote_conflict_requires_explicit_replacement(launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    old = '{"mcpServers":{"spotify":{"url":"https://private.test", "auth":{"secret":"fake-secret"}, "disabled":true}}}'
    conflict = merge_client_config("cursor", old, launch)
    assert conflict.conflict and not conflict.changed
    result = merge_client_config("cursor", old, launch, replace_conflict=True)
    entry = json.loads(result.text)["mcpServers"]["spotify"]
    assert "url" not in entry and "auth" not in entry
    assert entry["disabled"] is True
    assert entry["type"] == "stdio"


def test_unknown_command_is_conflict(launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    assert merge_client_config("cursor", '{"mcpServers":{"spotify":{"command":"unrelated"}}}', launch).conflict


def test_module_launch_is_recognized(launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    result = merge_client_config("claude-code", '{"mcpServers":{"spotify":{"command":"/old/python", "args":["-m","spotify_mcp_assistant.server"]}}}', launch)
    assert result.changed and not result.conflict


def test_legacy_credentials_removed_from_client_env(launch):
    from spotify_mcp_assistant.client_config import merge_client_config
    result = merge_client_config("cursor", '{"mcpServers":{"spotify":{"command":"spotify-mcp-assistant","env":{"SPOTIFY_CLIENT_SECRET":"fake-secret","SPOTIFY_CLIENT_ID":"old", "SPOTIFY_REDIRECT_URI":"old", "OTHER":"keep"}}}}', launch)
    env = json.loads(result.text)["mcpServers"]["spotify"]["env"]
    assert "SPOTIFY_CLIENT_SECRET" not in env
    assert "SPOTIFY_CLIENT_ID" not in env
    assert "SPOTIFY_REDIRECT_URI" not in env
    assert env["OTHER"] == "keep"
