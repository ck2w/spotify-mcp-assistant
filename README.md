# 🎵 Spotify MCP Assistant

Find and play music through conversations in Claude Code or Claude Desktop:

**Search → Choose a track and device → Preview → Confirm → Play → Verify**

An independent Python project built with **FastMCP over stdio**. Version 0.2.0 exposes **32 tools** for tracks, playlists, playback, queues, and favorites. Claude and other MCP clients handle conversations and orchestration; this project is the MCP server.

## 🧭 Start here

1. [Install the project](#-1-install-the-project)
2. [Configure Spotify and authorize](#-2-configure-spotify-and-authorize)
3. Connect [Claude Code](#-3-connect-claude-code) or [Claude Desktop](#-4-connect-claude-desktop)
4. [Start using the assistant](#-5-start-using-the-assistant)

Both clients can use the same private configuration directory and authorization.

## 📦 1. Install the project

### Prerequisites

- **Python ≥ 3.10**. This project was verified with Python 3.12.
- **Poetry**. If needed, follow the [Poetry installation guide](https://python-poetry.org/docs/#installation).
- A **Spotify Premium** account for playback.
- Claude Code or Claude Desktop.

After downloading or cloning this repository, enter its directory and run:

```bash
cd spotify-mcp-assistant

# Create a separate environment inside this project
POETRY_VIRTUALENVS_IN_PROJECT=true poetry env use python3.12

# Install the project and dependencies from poetry.lock
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install

# Check the selected Python version
poetry run python --version
```

If `python3.12` is unavailable, pass the absolute path of a supported interpreter to `poetry env use`. Check your system's `python3` version before using it.

**`.venv` is this project's own environment directory.** Dependencies are installed there, rather than in Conda base or another Conda environment. Use `poetry run` without manually activating the environment.

## 🔑 2. Configure Spotify and authorize

### ① Set up your developer application

Open the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create or open your own application:

- Obtain its **Client ID** and **Client Secret**.
- Add and save this exact Redirect URI:

```text
http://127.0.0.1:8888/callback
```

The callback address and port are fixed in this project. Keep them unchanged and do not substitute `localhost`. Development-mode application owners need Premium, and the authorizing account must meet the application's user access requirements. See Spotify's [application documentation](https://developer.spotify.com/documentation/web-api/concepts/apps), [redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri), and [development-mode requirements](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

### ② Fill in your private configuration

The following commands are for macOS. Run them from the project directory:

```bash
mkdir -p ~/.config/spotify-mcp-assistant

# Preserve an existing configuration
cp -n .env.example ~/.config/spotify-mcp-assistant/.env

nano ~/.config/spotify-mcp-assistant/.env
```

Enter your application credentials:

```dotenv
SPOTIFY_CLIENT_ID=YOUR_CLIENT_ID
SPOTIFY_CLIENT_SECRET=YOUR_CLIENT_SECRET
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

In nano, press **Control+O → Enter** to save, then **Control+X** to exit.

Private files live in `~/.config/spotify-mcp-assistant`, outside the repository. Client registration files do not need your Spotify secret.

### ③ Authorize once

```bash
poetry run spotify-mcp-auth
```

Your browser opens Spotify's authorization page. Confirm your account and grant access. The following terminal message indicates completion:

```text
Authorization completed. Token cache saved.
```

The command creates a new `.spotify_token.json` in the private directory. Tokens refresh when needed. Tool calls never open an authorization browser automatically.

> Authorize using your own configuration. Do not copy real `.env` files or cached tokens from another repository. Port 8888 must be available.

### Optional: use a different private directory

`SPOTIFY_CONFIG_DIR` overrides the default directory. It must be an absolute path, optionally starting with `~`; empty and relative values are rejected.

Create and populate `.env` in your chosen directory first, then authorize:

```bash
SPOTIFY_CONFIG_DIR=/ABSOLUTE/PATH/TO/PRIVATE/CONFIG poetry run spotify-mcp-auth
```

When using a custom directory, pass the same `SPOTIFY_CONFIG_DIR` to the server in each MCP client's configuration.

## 💻 3. Connect Claude Code

From the project directory, run:

```bash
claude mcp add --scope project --transport stdio spotify \
  -- "$(poetry env info --path)/bin/python" \
  -m spotify_mcp_assistant.server
```

This registers the server in the project's `.mcp.json`. The interpreter comes from the Poetry environment; no `PYTHONPATH` is needed.

Start a new Claude Code session:

```bash
claude
```

Approve the project's `spotify` MCP server when prompted. Inside the session, enter:

```text
/mcp
```

Confirm that `spotify` is connected. You can also run `claude mcp get spotify` from the project terminal. If its status is **Pending approval**, enter Claude Code and approve the server first.

**Claude Code starts the server automatically. You do not need a separate server terminal.** See the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).

For a custom private directory, use this registration command instead. Replace the directory placeholder with your own path:

```bash
claude mcp add --scope project \
  --env SPOTIFY_CONFIG_DIR=/ABSOLUTE/PATH/TO/PRIVATE/CONFIG \
  --transport stdio spotify \
  -- "$(poetry env info --path)/bin/python" \
  -m spotify_mcp_assistant.server
```

## 🖥️ 4. Connect Claude Desktop

Claude Desktop uses a separate configuration file, so register the server there too.

### ① Find the interpreter path

From the project terminal, run:

```bash
poetry run python -c "import sys; print(sys.executable)"
```

Copy the complete output. It becomes the `command` value below.

### ② Edit the desktop configuration

On macOS, use the menu bar: **Claude → Settings → Developer → Edit Config**. The configuration file is located at:

```text
~/Library/Application Support/Claude/claude_desktop_config.json
```

If you have no other MCP servers, use this complete configuration. Replace the `command` placeholder with the absolute interpreter path copied above:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "/ABSOLUTE/PATH/TO/PROJECT/.venv/bin/python",
      "args": ["-m", "spotify_mcp_assistant.server"]
    }
  }
}
```

If other servers are already configured, add only the `spotify` entry to the existing `mcpServers` object and preserve everything else. Do not overwrite the desktop configuration with the project's `.mcp.json`.

The configuration above uses the default private directory. For a custom directory, add the `env` field from this object to the `spotify` entry:

```json
{
  "env": {
    "SPOTIFY_CONFIG_DIR": "/ABSOLUTE/PATH/TO/PRIVATE/CONFIG"
  }
}
```

Add a comma after the preceding `args` field. Do not include a Client Secret or token in this JSON.

### ③ Restart and check

Save the file, press **Command+Q to quit Claude Desktop completely**, then reopen it. Start a new chat and check the tools or connectors list for `spotify` and its 32 tools.

Claude Desktop starts the server automatically. You do not need to activate Poetry or run the server manually. See the [official MCP desktop setup guide](https://modelcontextprotocol.io/docs/develop/connect-local-servers).

## ▶️ 5. Start using the assistant

Open Spotify so the target device is discoverable. If no devices appear, try playing a track and then pausing it.

**First message: search and preview**

> Use spotify to search for Coldplay's Yellow and list devices. Let me choose the track and device, then preview with dry_run=true. Stop after the preview and wait for a new confirmation message. Do not play yet.

**After selecting a track and device and seeing the preview, send a new message:**

> I confirm the previewed track and device. Play using the same parameters, then query playback state to verify. If the result is unknown or state is delayed, check state first rather than sending another playback request.

Keep these behaviors in mind:

- **Preview is not audio playback.** It checks the device without sending a playback PUT. It does not verify track existence or playability.
- **Confirmation is an assistant instruction.** The server has no approval token; a client can still call `dry_run=False` directly.
- **Playback starts from the beginning.** It does not resume saved progress.
- **`submitted` does not mean verified.** Query state and check that the track URI and device ID match and `is_playing=True`.
- Changing the track or device requires another preview and confirmation. Do not automatically switch devices or repeat playback requests.

## 🧰 32 tools

| Group | Tools |
|---|---|
| Tracks | `search_tracks`, `get_track` |
| Playlist reads | `list_playlists`, `get_playlist`, `get_playlist_tracks` |
| Playlist mutations | `create_playlist`, `update_playlist_details`, `add_playlist_tracks`, `remove_playlist_tracks`, `replace_playlist_tracks`, `reorder_playlist_tracks` |
| Playlist library | `save_playlist`, `unsave_playlist` |
| Playback and devices | `list_devices`, `get_playback_state`, `play_track`, `play_playlist`, `transfer_playback` |
| Direct controls | `pause_playback`, `resume_playback`, `next_track`, `previous_track`, `seek_playback`, `set_volume`, `set_shuffle`, `set_repeat` |
| Queue | `get_queue`, `add_to_queue` |
| Saved songs | `get_saved_tracks`, `save_tracks`, `remove_saved_tracks`, `check_saved_tracks` |

**Direct controls execute immediately** for clear user requests, always on an explicit device ID. Other writes default to `dry_run=true`: preview, wait for a new user confirmation, then execute identical parameters with `false`. Confirmation is a client responsibility; the server cannot verify the conversation.

- Track and playlist URIs are `spotify:track:...` and `spotify:playlist:...`; `playlist_id` is the bare ID. Use values returned by reads, not guessed names.
- `create_playlist` defaults to private and creates an empty playlist. Only execution returns its real ID. Preview adding songs separately, then confirm and execute.
- Content-change previews expose `snapshot_id`; pass it as `expected_snapshot_id` at execution. A mismatch requires another read and preview. This is a precheck, not an atomic lock.
- Playlist/favorites pages default to 20, maximum 50. Use `next_offset` until absent. Search retains its original 1–10 result limit.
- Add/remove songs and favorites accept 1–500 URIs, sent sequentially in batches of 100 for playlist items or 40 for library operations. Adding keeps duplicates; URI removal and saving deduplicate and report the mapping.
- Replacement accepts 0–100 tracks in one request and overwrites **all contents**; an empty list clears the playlist. Reordering uses zero-based positions including non-track/unavailable entries.
- `resume_playback` preserves existing context; `play_track` starts a song from the beginning. `transfer_playback` defaults to `play=false`. No audio streaming/preview is provided.
- `save_playlist` saves an existing playlist, and `unsave_playlist` removes it from your library. Neither copies nor deletes its contents.

Business results use `ok/data/error`. A batch failure can return `ok=false` **with progress in data**. `submitted` means the API accepted the request, not verified state. `partial` preserves completed batches; `unknown` identifies a batch that may have executed. Read remote state before deciding to retry. The server does not automatically replay writes, roll back batches, or persist task progress.

See [client workflow recipes and evidence boundaries](docs/workflows.md).

### Upgrade authorization

Existing playback-only tokens need additional permissions. Run:

```bash
poetry run spotify-mcp-auth
```

The authorization command requests playback read/currently-playing/modify, playlist read-private/read-collaborative/modify-private/modify-public, and library read/modify permissions. Reuse the same private configuration directory. Tools never open an authorization browser automatically.

Known missing scopes return `insufficient_scope`. An old token without scope metadata is allowed to reach the API; a 403 can also reflect account, application, resource, or device restrictions.

Current endpoints use `/me/playlists`, `/playlists/{id}/items`, and URI-based `/me/library`. Development-mode playlist contents can be restricted to playlists you own or collaborate on; inaccessible content is not an empty playlist. Consult the [migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide) and newer [July 2026 changes](https://developer.spotify.com/documentation/web-api/references/changes/july-2026) when checking application access and quotas.

## 🛠️ Troubleshooting

| Symptom | Next action |
|---|---|
| Claude Code shows Pending approval | Start `claude` in the project directory, approve `spotify`, then check `/mcp`. |
| Claude Desktop does not show tools | Check the JSON and absolute interpreter path, then fully quit and restart. macOS logs are in `~/Library/Logs/Claude`. |
| `auth_required` | Run `poetry run spotify-mcp-auth` from the project directory, using the same private directory as the client. |
| `insufficient_scope` | Reauthorize with `spotify-mcp-auth` to grant management permissions. |
| `oauth_config_error` / `forbidden` | Check credentials, granted scopes, account eligibility, and application user access. |
| No devices / `device_unavailable` | Open Spotify, play then pause, list devices again, and select a current ID. |
| `device_restricted` | Ask the user to select another device. |
| `rate_limited` | Wait according to `retry_after_seconds` when provided. |
| `playback_result_unknown` | Read state first. The request may have reached Spotify; do not immediately replay. |

Reads retry an API 401 at most once after refreshing the token. Business writes are not automatically retried. Write timeouts and ambiguous server failures require state inspection; OAuth refresh failures before submission are reported separately. Token/configuration errors are sanitized in tool results; the standalone authorization command reports its own failures.

## 🧪 Development and verification

```bash
poetry check --lock
poetry run pytest tests -v
poetry build
```

The suite verifies all tool groups, schema bounds, default previews, OAuth scopes, pagination, device checks, sequential batching, partial/unknown outcomes, and three simulated MCP workflows. It uses fake data and HTTP responses without real credentials or devices.

Mocked tests do not establish live OAuth, playback, or client confirmation behavior. Follow [the workflow acceptance guide](docs/workflows.md) for real runs and record results separately.

To verify installed stdio discovery from outside the repository:

```bash
poetry run python tests/check_stdio.py \
  --server-python /ABSOLUTE/PATH/TO/INSTALLED/VENV/bin/python \
  --cwd /ABSOLUTE/PATH/OUTSIDE/REPOSITORY
```

This checks both installed entry points and all 32 tools using an empty temporary private configuration; it does not contact Spotify.

To start or inspect entry points directly:

```bash
poetry run spotify-mcp-assistant
poetry run python -m spotify_mcp_assistant.server
poetry run python -m spotify_mcp_assistant.oauth
```
